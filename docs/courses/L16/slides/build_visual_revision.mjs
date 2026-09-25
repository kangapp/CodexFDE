import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const root='D:/work/CodexFDE';
const runtime='C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const skill='C:/Users/Administrator/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const {Presentation,PresentationFile}=await import(pathToFileURL(runtime+'/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const revision=process.env.L16_REVISION||'v1';
const build=root+'/.runtime/l16-visual-29-'+revision;
const output=root+'/docs/courses/L16/slides/L16-在新环境接手并完成现场新需求-图文分层版-29页-'+revision+'.pptx';
const navy='#142939',paper='#FAF9F6',gold='#B78B43',muted='#536A7B',font='Microsoft YaHei';
const sections=['接手：让已有系统运行起来','开发：通过工作台完成新需求','交付：交回可继续使用的版本','结课：下一项需求能复用什么'];
const old='assets/imagegen-20260920/',fresh='assets/imagegen-20260923/';
const specs=[
{cover:true,title:'在新环境接手，\n并完成现场新需求'},
{title:'离开原作者，系统还能继续交付吗？',point:'新环境检验可接手，新需求检验可继续开发。',caseTitle:'库存查找',caseText:'林舟交接工作台与 FlowERP。陈珂在新环境接手后，周宁提出库存查找需求。',body:'人确认需求并接受结果，Codex 协助实现。\n工作台组织执行、检查和审核，留下可追查的过程。',foot:'人物、情节和配图均为教学示意。个人实践从当前版本的真实缺口开始。'},
{title:'Vibe Coding、Spec Coding 与 Harness 工程',point:'开发方式逐步增加判断依据，三种方式可以配合使用。',img:fresh+'01-methods.png',cue:'读图：先试出结果，再按规格判断，通过工程机制约束执行。',source:'https://github.github.com/spec-kit/',notes:'Vibe Coding 依赖自然语言与直观反馈探索。Spec Coding 先明确范围与验收标准。Harness 工程把授权、执行、验证、停止和人审落实到工作台。本课学习路线，并非行业统一等级。图中界面与文档只作概念示意，具体实现以本次 Spec 为准。'},
{title:'搜索框出现了，需求还没有说清',point:'Spec 将“看起来能用”变成可核对的要求。',caseTitle:'同一个搜索框，三项未回答的问题',caseText:'第二页商品能找到吗？\n其他组织的同名商品会泄露吗？\n读取失败会不会误报为“没有库存”？',body:'先确认查找范围、权限和失败表现，再据此实现与验收。',foot:'当前页列表变短，只能说明当前页发生了筛选。'},
{title:'FDE：深入现场，负责到实际可用',point:'Forward-Deployed Engineering，面向真实业务问题的工程工作方式。',img:fresh+'02-fde.png',cue:'读图：理解接单问题，交付可用查询，再根据使用反馈修订。',source:'https://jobs.lever.co/palantir/5168e8fd-fec1-4fea-b7a1-81bdaea65850',notes:'岗位 FDE 也常指 Forward-Deployed Engineer，前线部署工程师。Vibe、Spec、Harness 说明怎样开发和交付，FDE 说明为谁解决问题并负责到什么结果。'},
{title:'本课用三个循环组织 FDE 工作',point:'现场决定要解决什么，交付与能力改进围绕它展开。',rows:[['现场循环','了解使用方式和约束，试用后修正对问题的理解。'],['交付循环','工作台组织实现、检查与返工，由人接受具体版本。'],['能力循环','把反复出现的问题补成检查或经验，再由后续任务验证。']],foot:'这是本课的组织方式。保存经验之后，仍需要后续采用与复验。'},
{section:0,question:'离开作者电脑，\n哪些条件必须重建？'},
{part:0,title:'交付摘要说明现状，也暴露隐含条件',point:'接手需要还原版本、运行条件和未解决问题。',caseTitle:'说明只写了“启动服务”',caseText:'陈珂启动了工作台，却不知道 FlowERP 在哪里。\n作者电脑上的项目路径，成了别人无法重建的隐含条件。',body:'交接说明应给出两个仓库的版本、依赖、配置和数据位置。',foot:'补回遗漏后，再由接手者按说明验证。'},
{part:0,title:'三处环境分别承担不同职责',point:'保留起点、验证重建、开发新需求，才能定位变化来自哪里。',img:old+'01-environments.png',cue:'读图：左侧保留交接版本，中间验证重建，右侧承载新开发。'},
{part:0,title:'工作台与 FlowERP 保存不同的事实',point:'研发记录和业务数据需要分别确认。',img:old+'02-two-systems.png',cue:'读图：工作台保存研发过程，FlowERP 保存商品、库存和订单。'},
{part:0,title:'新容器仍可能读到旧数据',point:'容器减少程序运行差异，配置和数据仍需单独核对。',rows:[['镜像','封装程序与依赖，确定运行哪一版程序。'],['配置','决定实际连接哪个地址、客户项目和数据库。'],['数据卷','可以跨容器保留数据，新建容器不代表空库。']],foot:'冷启动要重新建立运行条件。只打开新终端，仍可能沿用旧环境。'},
{part:0,title:'健康检查只覆盖它实际检查的条件',point:'业务操作继续验证目标实例和真实数据读写。',caseTitle:'服务健康，却连接着作者的旧电脑',caseText:'先核对实际地址和版本。\n在新环境建立商品并重新查询，再从工作台查回一项任务。',body:'已有操作正常后，新需求检查失败才更可能来自能力缺失。',foot:'分别验证工作台与客户项目，不能用一个健康响应替代两套系统的检查。'},
{section:1,question:'新要求怎样成为\n可接受的产品增量？'},
{part:1,title:'查找范围决定实现与验收',point:'当前页筛选和跨分页查询，需要不同的要求。',img:old+'05-clarify.png',cue:'读图：比较两种查找范围，再确认当前版本缺少哪种能力。'},
{part:1,title:'验收数据要覆盖容易遗漏的边界',point:'先在原版本运行检查，确认它能识别真实缺口。',caseTitle:'当前组织内，按名称跨分页查库存',caseText:'第二页商品：应能查到。\n其他组织的同名商品：不应泄露。\n模糊推荐与批量修改：不在本次范围。',body:'连不上服务属于环境问题。功能已经存在，就重新寻找真实缺口。',foot:'新增检查验证新要求，既有阻断 Eval 保护原有能力。'},
{part:1,title:'授权、检查和停止条件共同约束执行',point:'从工作台首页“事项与决策”组织本次开发。',img:old+'06-delivery.png',cue:'读图：确认范围后执行修改，检查结果，再由人接受或打回。',notes:'指定候选目录、允许文件、验收命令和修复上限。候选是本次准备交付的代码版本，Diff、报告与审核必须对应它。'},
{part:1,title:'打回要能复现，接受要对应新版本',point:'具体输入与预期结果，比“功能不好用”更能帮助定位问题。',caseTitle:'第二页商品返回空结果',caseText:'陈珂用同一商品复现遗漏，打回第一版。\nCodex 修订后，陈珂重跑原检查和新增用例，再决定是否接受。',body:'保留第一版失败，后来的通过报告关联修订版。',foot:'独立复验与具名接受针对同一候选，执行者的完成声明不能替代它们。'},
{part:1,title:'不同失败需要处理不同对象',point:'先判断哪一层出了问题，再决定如何修复。',img:old+'07-failures.png',cue:'读图：业务拒绝查数据保护，读取失败查提示，研发打回查需求满足。'},
{part:1,title:'修复继续到哪里，工作台必须说清',point:'Loop 控制修复边界，Graph 区分执行、复验与接受。',rows:[['继续','检查仍失败，但有进展、未越界且预算充足。'],['停止','达到上限、需要新授权或证据不足时，交回人判断。'],['接受','新候选通过检查后，仍由人依据同版材料作决定。']],foot:'旧经验可以帮助选择修法，本次 Spec、Diff 和 Eval 仍需独立成立。'},
{section:2,question:'交付后怎样使用、\n追查与处理故障？'},
{part:2,title:'实际使用会揭示新的需求',point:'原要求通过验收后，新增反馈仍需要确认范围。',img:fresh+'04-feedback.png',cue:'读图：名称查找已经通过，编码查找是否开发，要重新确认。'},
{part:2,title:'交付记录帮助解释“今天为什么又不行”',point:'摘要与结果导出连接已交付版本，反馈连接下一次改进。',img:old+'08-evidence.png',cue:'读图：核对同一版本、同一组织与同一组数据，再追查变化。',notes:'本次须产生实际结果导出和有来源的反馈写入。摘要、Spec、差异、报告和人审可以互相回查。图片为教学索引，不代表个人已验收。'},
{part:2,title:'回退程序与恢复数据，需要分别判断',point:'切回旧程序，不会撤销已经发生的出入库。',img:old+'03-rollback.png',cue:'读图：保护现场、核对兼容条件，再在独立副本验证恢复。'},
{part:2,title:'还原备份点，不等于还原当前业务',point:'备份之后新增的业务，必须另行对账。',img:old+'04-restore.png',cue:'案例：备份 8 件，后来入库 2 件。恢复副本仍是 8 件，差额由业务负责人判断。'},
{section:3,question:'这次失败的教训，\n怎样帮助下次交付？'},
{part:3,title:'同一个查询遗漏，可能要改三个地方',point:'先定位缺口，再决定修规格、补检查，还是修工作台。',img:fresh+'03-failure.png',cue:'读图：三行是不同原因与改进位置，不是依次执行的三个步骤。'},
{part:3,title:'能复用的是方法，新业务仍需新验证',point:'库存查询的经验可以提示风险，不能证明销售导出正确。',caseTitle:'从库存查询到销售导出',caseText:'“分页可能遗漏”提醒你检查导出是否覆盖全部结果。\n销售字段、权限、金额计算和失败状态，仍需重新确认。',body:'工作台复用任务组织和审核机制，FlowERP 在新规则下接受检查。',foot:'把实际采用结果写回经验，才能知道它是否帮助了后续任务。'},
{part:3,title:'交付边界要具体到别人能作判断',point:'交回可用版本，也要说明尚未验证的条件和剩余风险。',caseTitle:'查询正确，但数据增大后变慢',caseText:'说明当前验证过的数据规模、变慢时的现象和后续处理安排。\n接手者才能判断何时需要优化，怎样检验改善。',body:'干净环境可启动、阻断 Eval 通过、审核可追查，且仓库无密钥。\nLoop 如实停止时，要同时说明产品还缺哪些条件。',foot:'结业检查表与五分钟答辩稿见实践手册。正文关注交付判断，操作记录按实际结果填写。'},
{part:3,title:'课程结束，下一项真实需求仍会到来',point:'工作台组织人与 Codex 协作，FlowERP 持续获得可验证的增量。',rows:[['Q1','系统换了环境，哪些隐含条件最容易遗漏？'],['Q2','第二页商品查不到，你凭什么决定改哪里？'],['Q3','旧经验用于新需求时，哪些规则必须重新验证？']],foot:'接下来：用自己的工作台完成下一项范围受控的真实需求。'}
];
if(specs.length!==29)throw new Error('unexpected slide count');
const p=Presentation.create({slideSize:{width:1440,height:810}});
function text(s,t,x,y,w,h,size=30,color=navy,bold=false,italic=false){const q=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});q.text=t;q.text.style={typeface:font,fontSize:size,color,bold,italic,autoFit:'none'};return q;}
await fs.mkdir(build,{recursive:true});
for(let i=0;i<specs.length;i++){
 const d=specs[i],s=p.slides.add(),dark=d.cover||d.section!==undefined;s.background.fill=dark?navy:paper;
 if(d.cover){text(s,'Codex AI 工程交付行动营',80,60,1280,60,32,'#CFD7DE');text(s,'L16',80,205,1200,100,84,gold,true);text(s,d.title,80,350,1280,210,64,'#FFFFFF',true);text(s,'接手已有系统，完成新的开发，交回可用版本。',80,660,1280,70,30,'#CFD7DE');}
 else if(d.section!==undefined){text(s,'本讲目录',80,75,1200,70,44,'#FFFFFF',true);sections.forEach((t,j)=>text(s,String(j+1).padStart(2,'0')+'  '+t,80,225+j*95,900,72,32,j===d.section?gold:'#A9BAC8',j===d.section));text(s,d.question,1000,280,360,240,36,'#FFFFFF',true);}
 else{
 text(s,d.part===undefined?'L16 / 课程回顾':'L16 / '+sections[d.part].split('：')[0],80,38,1280,44,24,muted);
 text(s,d.title,80,103,1280,80,42,navy,true);
 text(s,d.point,80,190,1280,76,30,navy,true);
 if(d.img){s.images.add({blob:new Uint8Array(await fs.readFile(root+'/docs/courses/L16/'+d.img)),contentType:'image/png',alt:d.title+'（教学示意）',fit:'contain',position:{left:80,top:260,width:1280,height:465}});text(s,d.cue,80,735,1280,40,23,muted,false,true);}
 if(d.rows){d.rows.forEach(([a,b],j)=>{text(s,a,80,300+j*116,240,70,30,gold,true);text(s,b,350,300+j*116,995,95,30);});}
 if(d.caseTitle){text(s,'案例  '+d.caseTitle,100,302,1230,60,28,gold,true);text(s,d.caseText,100,378,1220,174,32);text(s,d.body,80,579,1280,110,29);}
 if(d.foot)text(s,d.foot,80,711,1280,56,23,muted);
 }
 text(s,String(i+1).padStart(2,'0'),80,775,100,30,18,dark?'#A9BAC8':muted);
 s.speakerNotes.textFrame.setText('依据：docs/courses/L16/辅导资料.md。\n'+(d.title||sections[d.section])+'\n'+(d.point||'')+'\n'+(d.notes||'')+'\n'+(d.foot||'')+(d.source?'\n概念参考：'+d.source:'')+(d.img?'\n教学图：docs/courses/L16/'+d.img:'')+'\n文中人物、情节和图片用于教学说明，不代表个人运行与验收结果。');
}
const candidate=build+'/candidate.pptx';await(await PresentationFile.exportPptx(p)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:output,pythonExecutable:runtime+'/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','13716000,7715250','--validate-heading-fit'],explicitTotalSlideCount:specs.length,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:build+'/validation.json'});
console.log(output);
