"""Local desktop entry with an explicit, identity-checked workbench restart."""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
import webbrowser

from .runtime_lease import WorkbenchRuntimeLease

ROOT = Path(__file__).resolve().parent.parent


def listener_process(port: int) -> tuple[int, list[str]]:
    """Read the actual listener and parse its Windows command line without a shell."""
    if os.name != 'nt':
        raise RuntimeError('自动重启目前支持 Windows；请先停止原工作台服务，或使用 --reuse')
    script = ('[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); '
              f'$owners = @(Get-NetTCPConnection -LocalPort {int(port)} -State Listen '
              '| Select-Object -ExpandProperty OwningProcess -Unique); '
              'if ($owners.Count -ne 1) { throw "Listener is not unique" }; '
              'Get-CimInstance Win32_Process -Filter ("ProcessId=" + $owners[0]) '
              '| Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                            capture_output=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError('无法核对旧服务进程，未停止任何进程')
    try:
        data = json.loads(result.stdout.decode('utf-8-sig'))
        import ctypes
        from ctypes import wintypes
        parse = ctypes.windll.shell32.CommandLineToArgvW
        parse.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
        parse.restype = ctypes.POINTER(wintypes.LPWSTR)
        count = ctypes.c_int()
        pointer = parse(data['CommandLine'], ctypes.byref(count))
        if not pointer:
            raise ValueError('Missing command line')
        try:
            arguments = [pointer[i] for i in range(count.value)]
        finally:
            free = ctypes.windll.kernel32.LocalFree
            free.argtypes = [ctypes.c_void_p]
            free.restype = ctypes.c_void_p
            free(ctypes.cast(pointer, ctypes.c_void_p))
        return int(data['ProcessId']), arguments
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeError('无法识别旧服务命令，未停止任何进程') from error


def stop_workbench(runtime: Path, port: int, timeout: float = 20) -> None:
    """Only stop the verified workbench listener; never kill a process tree."""
    if inspect_service(port, runtime) != 'same':
        raise RuntimeError('旧服务身份已变化，取消重启')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def read(path):
        with opener.open(f'http://127.0.0.1:{port}{path}', timeout=5) as response:
            return json.load(response)
    try:
        for item in read('/api/v1/initiatives')['items']:
            flow = read('/api/v1/initiatives/' + item['id'] + '/workflow')
            if flow.get('stage') in {'researching', 'queued', 'executing', 'cancelling', 'integrating'}:
                raise RuntimeError('工作台仍有运行中的事项，请先在页面停止任务并等待结束，再重启')
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RuntimeError('无法核对运行中的事项，未停止旧服务') from error
    pid, arguments = listener_process(port)
    try:
        module = arguments.index('-m')
        location = arguments[arguments.index('--runtime-dir') + 1]
        listener_port = arguments[arguments.index('--port') + 1]
        matches = (arguments[module + 1:module + 3] == ['workbench.cli', 'serve-workbench']
                   and Path(location).is_absolute() and Path(location).resolve() == runtime.resolve()
                   and int(listener_port) == port and pid > 0 and pid != os.getpid())
    except (ValueError, IndexError):
        matches = False
    if not matches:
        raise RuntimeError('监听进程不是指定目录的工作台服务，未停止任何进程')
    print(f'正在重启工作台（端口 {port}，旧进程 {pid}），任务与证据保留。', flush=True)
    result = subprocess.run(['taskkill.exe', '/PID', str(pid), '/F'], capture_output=True,
                            timeout=15, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('未能停止旧工作台服务，请核对权限或原启动窗口')
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = inspect_service(port, runtime)
        if state == 'free':
            return
        if state == 'occupied':
            raise RuntimeError('端口已被其他服务接管，取消启动')
        time.sleep(.2)
    raise RuntimeError('旧服务尚未释放端口，未启动第二个实例')


def wait_for_product_release(runtime: Path, *, timeout: float = 35) -> None:
    """Wait for an existing writer lease without changing it or its owner."""
    database = runtime / 'flowerp.db'
    if not database.exists():
        return
    deadline = time.monotonic() + timeout
    announced = False
    while True:
        with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True, timeout=2)) as connection:
            exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='instance_leases'").fetchone()
            active = exists and connection.execute(
                "SELECT 1 FROM instance_leases WHERE lease_name='sqlite-primary-writer' AND expires_at>CURRENT_TIMESTAMP"
            ).fetchone()
        if not active:
            return
        if time.monotonic() >= deadline:
            raise RuntimeError('FlowERP 的数据仍由另一个实例使用。工作台可以继续打开；请核对其他 FlowERP 窗口后再重开。')
        if not announced:
            print('FlowERP 正在等待上次运行释放数据，通常不超过 35 秒，请保留窗口，无需重复点击。', flush=True)
            announced = True
        time.sleep(.5)


def inspect_service(port: int, runtime: Path, surface: str = 'workbench') -> str:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        endpoint = '/api/health' if surface == 'workbench' else '/api/v1/health/live'
        with opener.open(f'http://127.0.0.1:{port}{endpoint}', timeout=1) as response:
            data = json.load(response)
        if surface == 'flowerp' and isinstance(data, dict):
            identity = hashlib.sha256(os.path.normcase(str(runtime.resolve())).encode()).hexdigest()
            return 'same' if (data.get('service') == 'flowerp' and data.get('status') == 'ok'
                              and data.get('runtime_id') == identity) else 'occupied'
        if (isinstance(data, dict) and data.get('surface') == 'workbench' and data.get('status') == 'ok'
                and Path(data.get('runtime', '')).resolve() == runtime.resolve()):
            return 'same'
        return 'occupied'
    except (OSError, ValueError, TypeError):
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=.3):
                return 'occupied'
        except OSError:
            return 'free'


def launch(runtime: Path, port: int = 8001, *, timeout: float = 20,
           surface: str = 'workbench', erp_port: int = 8000, restart: bool = False) -> dict:
    if surface not in {'workbench', 'flowerp'}:
        raise ValueError('未知的本地服务')
    label = '工作台' if surface == 'workbench' else 'FlowERP'
    runtime = runtime.resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    # Serialize launchers separately from the server's lifetime lock.
    with WorkbenchRuntimeLease(runtime / ('desktop-launch-' + surface)):
        state = inspect_service(port, runtime, surface)
        url = f'http://127.0.0.1:{port}'
        restarted = False
        if state == 'same' and restart and surface == 'workbench':
            stop_workbench(runtime, port, timeout)
            restarted = True
            state = inspect_service(port, runtime, surface)
        if state == 'same':
            return {'state': 'reused', 'url': url}
        if state != 'free':
            raise RuntimeError(f'端口 {port} 已由其他服务或另一份任务目录使用。请核对原窗口，不要重复启动。')
        if surface == 'flowerp':
            wait_for_product_release(runtime)
            # Another launcher may have acquired the port while we waited.
            state = inspect_service(port, runtime, surface)
            if state == 'same':
                return {'state': 'reused', 'url': url}
            if state != 'free':
                raise RuntimeError(f'端口 {port} 已被使用，请核对已打开的客户项目。')
        logs = runtime / 'startup-logs'
        logs.mkdir(exist_ok=True)
        stamp = time.strftime('%Y%m%d-%H%M%S') + f'-{time.time_ns()}'
        log = logs / f'{surface}-{stamp}.log'
        command = [sys.executable, '-X', 'utf8', '-m', 'workbench.cli',
                   'serve-workbench' if surface == 'workbench' else 'serve',
                   '--host', '127.0.0.1', '--port', str(port), '--runtime-dir', str(runtime)]
        if surface == 'workbench':
            command += ['--enable-code-execution', '--erp-url', f'http://127.0.0.1:{erp_port}']
        working_directory = ROOT
        if surface == 'flowerp':
            from .external_project import command as product_command
            working_directory, command = product_command(['serve', '--host', '127.0.0.1',
                '--port', str(port), '--runtime-dir', str(runtime)])
        options = {'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
        with log.open('wb') as output:
            from .codex_options import headless_environment
            process = subprocess.Popen(command, cwd=working_directory, env=headless_environment(), stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=subprocess.STDOUT, **options)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'{label}未能启动。原因保存在：{log}')
            state = inspect_service(port, runtime, surface)
            if state == 'same':
                return {'state': 'restarted' if restarted else 'started', 'url': url, 'pid': process.pid, 'log': str(log)}
            time.sleep(.2)
        raise RuntimeError(f'{label}仍未就绪，请先查看启动日志，不要连续重试：{log}')


def main(argv=None):
    parser = argparse.ArgumentParser(description='打开个人研发工作台，保留原任务和启动记录')
    parser.add_argument('--runtime-dir', type=Path, help='显式覆盖工作台运行目录')
    parser.add_argument('--erp-runtime-dir', type=Path, help='显式覆盖 FlowERP 运行目录')
    parser.add_argument('--port', type=int, default=8001)
    parser.add_argument('--erp-port', type=int, default=8000)
    parser.add_argument('--open-browser', action='store_true')
    parser.add_argument('--reuse', action='store_true', help='复用已有工作台，不重启；默认重启同目录的旧工作台')
    args = parser.parse_args(argv)
    if not all(1 <= port <= 65535 for port in (args.port, args.erp_port)) or args.port == args.erp_port:
        parser.error('工作台和 FlowERP 必须使用 1 到 65535 之间的不同端口')
    from .runtime_paths import service_runtime
    try:
        workbench_runtime = service_runtime('workbench', args.runtime_dir, root=ROOT)
        erp_runtime = service_runtime('flowerp', args.erp_runtime_dir, root=ROOT)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    try:
        result = launch(workbench_runtime, args.port, erp_port=args.erp_port, restart=not args.reuse)
    except (OSError, RuntimeError, sqlite3.Error) as error:
        print(f'暂时无法打开工作台：{error}', file=sys.stderr)
        return 1
    failed = False
    try:
        result['flowerp'] = launch(erp_runtime, args.erp_port, surface='flowerp')
    except (OSError, RuntimeError, sqlite3.Error) as error:
        failed = True
        result['flowerp'] = {'state': 'unavailable', 'message': str(error)}
        print(f'工作台可用，但客户项目尚未就绪：{error}', file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False))
    if args.open_browser:
        webbrowser.open(result['url'])
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
