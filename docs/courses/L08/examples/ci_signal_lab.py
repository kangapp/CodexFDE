"""Run the actual Harness with a labelled teaching check and local CI adapter.

This tests exit propagation, not GitHub execution or product atomicity.
Each run uses a fresh temporary report and explicitly simulated run identity.
"""
from pathlib import Path
import argparse
import contextlib
import io
import json
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from eval import harness
from workbench.ci_evidence import build_envelope


def run(mode):
    def teaching_check():
        if mode != 'true-green':
            raise AssertionError('L08 teaching control failure; not a product incident')
        return 'L08 teaching control passed; not a product repair'

    with tempfile.TemporaryDirectory(prefix='l08-signal-') as temp:
        path = Path(temp) / 'report.json'
        log = io.StringIO()
        with patch.object(harness, 'EVALS', [('l08_teaching_signal', 'blocking', teaching_check)]), \
                patch.object(sys, 'argv', ['harness', '--suite', 'blocking', '--case',
                                          'l08_teaching_signal', '--report-path', str(path)]), \
                contextlib.redirect_stdout(log):
            harness_exit = harness.main()
        report = json.loads(path.read_text(encoding='utf8'))
        adapter_exit = 0 if mode == 'false-green' else harness_exit
        envelope = build_envelope(path, env={'GITHUB_SHA': 'SIMULATED-L08',
                                            'GITHUB_RUN_ID': 'SIMULATED-' + mode})
        assert path.is_file()
        return {'mode': mode, 'evidence_kind': 'local_harness_with_teaching_case',
                'report': report, 'envelope': envelope, 'harness_stdout': log.getvalue(),
                'harness_exit': harness_exit,
                'adapter_exit': adapter_exit, 'real_remote_run': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['false-green', 'true-red', 'true-green'])
    result = run(parser.parse_args().mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(result['adapter_exit'])
