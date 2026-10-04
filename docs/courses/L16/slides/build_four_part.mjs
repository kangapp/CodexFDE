import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const runtime='C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const {Presentation,PresentationFile}=await import(pathToFileURL(runtime+'/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const root='D:/work/CodexFDE';
const skill='C:/Users/Administrator/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const build=root+'/.runtime/l16-fde-27';
const output=root+'/docs/courses/L16/slides/L16-在新环境接手并完成现场新需求-FDE收束版-27页.pptx';
const p=Presentation.create({slideSize:{width:1440,height:810}});
const navy='#142939',paper='#FAF9F6',gold='#B78B43',muted='#536A7B';
const font='Microsoft YaHei';
function txt(s,t,x,y,w,h,size=32,color=navy,bold=false){const q=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});q.text=t;q.text.style={typeface:font,fontSize:size,color,bold,autoFit:'none'};return q;}
const sections=['接手：让已有系统运行起来','开发：通过工作台完成新需求','交付：交回可继续使用的版本','结课：解释判断与迁移'];
const specs=[
{cover:true,title:'在新环境接手，\n并完成现场新需求'},
{title:'一次接手，继续完成一项开发',rows:[['起点','L15 的交付摘要、个人研发工作台和 FlowERP。'],['现场','同伴启动系统后，业务人员提出一个未实现的小需求。'],['成果','交回可用的新版本，并留下能够复验的交付记录。']],foot:'你负责判断和授权，Codex 协助实现，工作台保存过程，同伴独立复验。'},
{section:0,question:'离开作者电脑，\n能否按说明运行？'},
{part:0,title:'从 L15 的交付摘要开始',rows:[['认版本','两个仓库分别来自哪里，使用哪次提交。'],['认现状','哪些功能已完成，哪些问题仍待处理。'],['认入口','如何安装、配置、启动，数据和日志在哪里。']],foot:'接手时发现说明缺步骤，就补回文档，再验证补充后的步骤。'},
{part:0,title:'原源码、新环境与本次候选',img:'01-environments.png',cue:'原源码确定版本。\n新环境验证重建。\n候选承载新开发。',foot:'后续命令、修改和报告都要注明针对哪个实际目录。'},
{part:0,title:'工作台与 FlowERP 分别运行',img:'02-two-systems.png',cue:'工作台保存研发记录。\nFlowERP 保存业务数据。\n两套数据分别核对。',foot:'工作台首页的“事项与决策”承接本次研发任务。'},
{part:0,title:'容器启动后，还要核对数据',rows:[['镜像','封装程序与依赖，记录版本和真实构建结果。'],['容器','运行程序，核对配置、日志和实际服务地址。'],['数据卷','保留运行数据，新建容器仍可能读到旧库。']],foot:'记录源码、依赖、数据和进程分别怎样隔离，才能解释本次冷启动。'},
{part:0,title:'用一次业务操作确认接手成功',rows:[['启动','两套服务启动，核对地址、版本和健康结果。'],['使用','完成一次已有业务操作，再读取指定记录。'],['回查','查回一项工作台任务，确认研发记录也能读取。']],foot:'完成标志：同伴按说明运行成功，发现的遗漏已补回文档。手册第 1～2 步。'},
{section:1,question:'怎样实现新需求，\n并得到同伴接受？'},
{part:1,title:'“快速查找库存”需要先说清范围',img:'05-clarify.png',cue:'查当前已加载列表？\n还是跨分页查全部？\n先调查当前能力。',foot:'教学案例。现场选择此前未实现的小需求，再确认权限、字段和失败表现。'},
{part:1,title:'本次 Spec 与修改前检查',rows:[['写清要求','保留来源、目标、非目标、约束、验收用例和完成定义。'],['找到缺口','新增检查应因目标能力缺失而失败，环境错误先排除。'],['限定范围','列明允许修改的文件、验收命令和停止条件。']],foot:'如果修改前就通过，先查明功能已存在，还是检查没有测到要求。'},
{part:1,title:'由工作台组织本次开发',img:'06-delivery.png',cue:'确认 Spec 与候选。\n授权 Codex 修改。\n检查后交同伴复验。',foot:'任务 ID、Spec、代码版本、Diff、报告与审核决定应能对应。'},
{part:1,title:'第一版遗漏要求时，怎样修订',rows:[['约定','周宁要求跨分页查找，第一版却只筛选当前页。'],['打回','陈珂查不到另一页商品，记录输入、预期、实际和版本。'],['修订','林舟组织 Codex 修订，重跑检查，再对新版本人审。']],foot:'教学反例。个人实践保留实际失败，后来的通过报告关联修订版本。'},
{part:1,title:'不同失败，处理对象不同',img:'07-failures.png',cue:'业务拒绝查数据保护。\n服务故障查运行状态。\n研发打回查需求满足。',foot:'展示真实打回及修订。一次服务断网不能证明研发审核经历过打回。'},
{part:1,title:'已有能力共同服务于这次开发',rows:[['要求与检查','Spec 明确要求，新增 Eval 与阻断 Eval 验证结果。'],['修复与决定','Loop 在限额内修复或退出，Graph 记录流转与人的决定。'],['经验与采用','引用 L15 经验的来源、版本和边界，用本次结果检验。']],foot:'完成标志：FlowERP 有真实增量，工作台可查到具名接受。手册第 3～4 步。'},
{section:2,question:'接手者如何使用、\n追查和处理故障？'},
{part:2,title:'把新版本交回使用者',img:'08-evidence.png',cue:'更新交接说明与摘要。\n导出本次实际结果。\n试用后写入真实反馈。',foot:'索引连接原始材料。抽取一句完成结论，核对需求、候选、报告与人审。'},
{part:2,title:'五个检查入口各自回答什么',rows:[['demo / blocking Eval','基础链路能否运行，阻断要求是否逐项满足。'],['Loop / Graph','修复如何结束，状态和审核决定是否可追踪。'],['feedback summary','本次反馈能否从同一运行目录查回。']],foot:'按手册第 5 步运行，记录输出、退出码和目录。演示审批不能代替独立人审。'},
{part:2,title:'发生故障后，先确认回退条件',img:'03-rollback.png',cue:'保留现场与备份。\n核对旧程序兼容性。\n先在副本中验证。',foot:'程序回滚不会撤销已经发生的出入库，恢复旧库可能丢失后续业务。'},
{part:2,title:'恢复副本里的 8 件意味着什么',img:'04-restore.png',cue:'备份时库存 8 件。\n后来入库 2 件。\n源库现在有 10 件。\n恢复副本仍为 8 件。',foot:'完成标志：记录恢复点、耗时、对账和剩余风险。差额处理由业务负责人决定。'},
{section:3,question:'这次怎样作判断？\n下次如何继续做？'},
{part:3,title:'五分钟，沿同一任务讲到交付',rows:[['第 1 分钟','怎样启动，交接说明遗漏了什么。'],['第 2 分钟','新需求是什么，自己为什么这样确定范围。'],['第 3 分钟','改了什么，失败怎样发现和修订。'],['第 4 分钟','谁接受哪个版本，导出和反馈在哪里。'],['第 5 分钟','有哪些技术债，条件变化后怎样重新验证。']],foot:'展示实际材料，保留未验证项。答辩稿与结业检查表对应手册第 7 步。'},
{part:3,title:'结业检查表对应真实材料',rows:[['接手与开发','干净环境可启动，需求形成 Spec 和代码，交付版本无密钥。'],['检查与审核','阻断 Eval 全通过，Loop 收敛或安全退出，Graph 决定可追踪。'],['交接与反馈','展示成功任务、真实打回、结果导出和反馈，摘要能回查。']],foot:'本讲综合检验 CLO-6 及前面各讲能力，个人判断和修订应有本人的记录。'},
{part:3,title:'从库存查询，继续到销售导出',rows:[['可以沿用','任务登记、授权、记录、独立复验与审核方法。'],['重新确认','销售字段、权限、金额计算及导出失败后的状态。'],['带走的成果','个人研发工作台组织协作，FlowERP 持续获得可验证的增量。']],foot:'Q1 接手时最容易遗漏什么？  Q2 旧经验哪些适用？  Q3 下一项需求怎样验收？'}
];
specs.splice(2,0,
{title:'Vibe Coding、Spec Coding 与 Harness 工程',rows:[['Vibe Coding','“帮我导出库存”。先看生成结果，按直观反馈调整。'],['Spec Coding','确认字段、数量计算与失败行为，让完成标准可检查。'],['Harness 工程','把规格、授权、执行、验证、修复和人审接成可复验流程。']],foot:'本课学习路线：快速探索、明确标准、受控交付。三种方式可以配合使用。',source:'https://github.github.com/spec-kit/'},
{title:'FDE：深入业务现场，负责到实际可用',rows:[['含义','Forward-Deployed Engineering，面向现场的工程工作方式。'],['现场问题','周宁要导出库存。先了解用途、计算口径与数据权限。'],['负责结果','与 Codex 实现，让使用者复验，再根据真实反馈修订。']],foot:'岗位 FDE 常指 Forward-Deployed Engineer。规格和 Harness 为现场交付提供方法。',source:'https://jobs.lever.co/palantir/5168e8fd-fec1-4fea-b7a1-81bdaea65850'},
{title:'本课怎样实践 FDE：现场、交付、能力',rows:[['现场','理解业务问题和约束，把模糊要求变成可验收的需求。'],['交付','工作台组织人与 Codex 实现、检查、返工和具名接受。'],['能力','把失败提炼成检查、经验或流程，交给后续任务验证。']],foot:'L16：新环境检验接手，现场需求检验交付，使用反馈检验效果。三循环为本课组织方式。'}
);
await fs.mkdir(build,{recursive:true});
for(let i=0;i<specs.length;i++){
 const d=specs[i],s=p.slides.add();s.background.fill=d.cover||d.section!==undefined?navy:paper;
 if(d.cover){txt(s,'Codex AI 工程交付行动营',80,60,1260,60,32,'#CFD7DE');txt(s,'L16',80,205,1200,100,84,gold,true);txt(s,d.title,80,350,1280,210,64,'#FFFFFF',true);txt(s,'接手已有系统，完成新的开发，交回可用版本。',80,660,1280,70,30,'#CFD7DE');}
 else if(d.section!==undefined){txt(s,'本讲目录',80,75,1200,70,44,'#FFFFFF',true);sections.forEach((t,j)=>txt(s,String(j+1).padStart(2,'0')+'  '+t,80,225+j*95,890,72,32,j===d.section?gold:'#A9BAC8',j===d.section));txt(s,d.question,1000,280,360,240,38,'#FFFFFF',true);}
 else{txt(s,d.part===undefined?'L16 / 本讲任务':'L16 / '+sections[d.part].split('：')[0],80,40,1280,45,24,muted);txt(s,d.title,80,108,1280,90,44,navy,true);
 if(d.img){s.images.add({blob:new Uint8Array(await fs.readFile(root+'/docs/courses/L16/assets/imagegen-20260920/'+d.img)),contentType:'image/png',alt:d.title+'（教学示意）',fit:'contain',position:{left:70,top:210,width:925,height:460}});txt(s,d.cue,1040,285,330,300,30,navy);}
 if(d.rows){const step=d.rows.length>3?87:138;d.rows.forEach(([a,b],j)=>{txt(s,a,80,235+j*step,265,72,30,gold,true);txt(s,b,365,235+j*step,975,110,31,navy);});}
 txt(s,d.foot,80,699,1280,64,24,muted);
 }
 txt(s,String(i+1).padStart(2,'0'),80,775,90,30,18,d.cover||d.section!==undefined?'#A9BAC8':muted);
 s.speakerNotes.textFrame.setText('依据：docs/courses/L16/辅导资料.md。'+(d.section!==undefined?'本节对应：'+sections[d.section]:d.title)+'。'+(d.foot||'')+'\n人物、查询案例与配图为教学说明，实际结果由学员采集。'+(d.source?'\n概念参考（2026-09-23 核对）：'+d.source:'')+(d.img?'\n图片来源：docs/courses/L16/assets/imagegen-20260920/'+d.img:''));
}
const candidate=build+'/candidate.pptx';await(await PresentationFile.exportPptx(p)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:output,pythonExecutable:runtime+'/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','13716000,7715250','--validate-heading-fit'],explicitTotalSlideCount:27,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:build+'/validation.json'});
console.log(output);
