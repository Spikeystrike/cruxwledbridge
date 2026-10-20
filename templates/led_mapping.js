'use strict';
const initial = __DATA__;
const api = __API__, previewUrl = __PREVIEW__;
const $ = id => document.getElementById(id);
const t = key => window.cruxI18n.t(key);
const clone = value => JSON.parse(JSON.stringify(value));
let layout = clone(initial.layout), active = initial.active;
layout.overrides ??= {}; layout.grip_surfaces ??= {};
layout.skipped_physical_ids ??= []; layout.lateral_tolerance ??= 0.35; layout.max_distance ??= 0.9;
layout.cable_path ??= null; layout.cable_start ??= 0; layout.edge_skips ??= [];
function normalizeGrid(g,i) {
    g.name ??= `LED ${i+1}`; g.surface ??= '1'; g.alternating ??= false;
    g.alternating_start_column ??= 0; g.led_start_corner ??= 'bottom_left'; g.led_direction ??= 'vertical';
    g.position_start_corner ??= g.led_start_corner; g.position_direction ??= g.led_direction;
    g.manual_positions ??= []; g.excluded_position_ids ??= []; g.subgrids ??= [];
    return g;
}
layout.grids.forEach(normalizeGrid);
let index=0, result=null, reviewed=false, dirty=false, view='grips', showLinks=false;
let selectedGrip=null, selectedLED=null, pickMode=null, picked=[], previewActive=false;
let gripGrids=initial.grip_grids;
const gridId=(g,i)=>g.id || `grid-${i+1}`;
const option=(text,value)=>{const o=document.createElement('option');o.textContent=text;o.value=value;return o;};
const grid=()=>layout.grids[index];
const gripLabel=p=>`${t('grid')} ${p.grid_index+1} · ${p.row===null?`${t('extra')} ${-p.position_id}`:`${t('row')} ${p.row+1}, ${t('col')} ${p.column+1}`}`;
function message(text,error=false){$('status').textContent=text;$('status').className=error?'error':'';}
function buttons(){
    $('activate').disabled=!reviewed || !!result?.unwired_count || !result?.grips.some(p=>p.below!==null || p.above!==null) || result?.unconfigured_led_ids.length>0 || result?.grips.some(p=>['below','above'].some(s=>p[`${s}_status`]==='ambiguous'));
    $('preview-grip').disabled=!reviewed || !selectedGrip;
    $('test-led').disabled=!reviewed || selectedLED===null;
    $('deactivate').disabled=!active;$('state').textContent=t(active?'active':'legacy');
    for(const [id,v] of [['grip-tab','grips'],['led-tab','leds'],['cable-tab','cable']]) $(id).setAttribute('aria-pressed',String(view===v));
    $('cable-tools').hidden=view!=='cable'; renderCableTools();
}
function changed(){reviewed=false;dirty=true;selectedLED=null;message(t('dirty'));buttons();}
function parseIDs(text){
    const ids=new Set();
    for(const token of text.trim().split(/[,;\s]+/).filter(Boolean)){
        const match=token.match(/^(\d+)(?:[-–](\d+))?$/);if(!match)throw new Error(t('invalidnumbers'));
        const from=Number(match[1]),to=Number(match[2]??from);
        if(!Number.isSafeInteger(from)||!Number.isSafeInteger(to)||to<from||to-from>10000)throw new Error(t('invalidnumbers'));
        for(let id=from;id<=to;id++)ids.add(id);if(ids.size>10000)throw new Error(t('invalidnumbers'));
    }return [...ids].sort((a,b)=>a-b);
}
function formToGrid(){
    const g=grid();if(!g)return;
    g.name=$('name').value;g.surface=$('surface').value.trim();g.r=Number($('rows').value);g.c=Number($('columns').value);
    g.alternating=$('alternating').checked;g.alternating_start_column=$('offset').checked?1:0;
    g.led_start_corner=$('start').value;g.led_direction=$('path').value;
    g.physical_start=$('physical-start').value===''?null:Number($('physical-start').value);
}
function capture(){formToGrid();layout.skipped_physical_ids=parseIDs($('skipped').value);layout.cable_start=Number($('cable-start').value);layout.lateral_tolerance=Number($('tolerance').value);layout.max_distance=Number($('distance').value);}
function renderForm(){
    for(const id of ['grid-select','cable-grid-select']){$(id).replaceChildren(...layout.grids.map((g,i)=>option(`${i+1}. ${g.name}`,i)));$(id).value=index;}
    const g=grid();$('grid-fields').hidden=!g;$('delete-grid').disabled=!g;$('earlier').disabled=index<=0;$('later').disabled=index>=layout.grids.length-1;
    for(const id of ['start','path','physical-start','select-subgrid','create-subgrid'])$(id).disabled=!g;
    if(g){
        for(const [id,value] of Object.entries({name:g.name,surface:g.surface,rows:g.r,columns:g.c,start:g.led_start_corner,path:g.led_direction,'physical-start':g.physical_start??''}))$(id).value=value;
        $('alternating').checked=!!g.alternating;$('offset').checked=g.alternating_start_column===1;
        $('position-select').replaceChildren(...(result?.leds||[]).filter(p=>p.grid_id===g.id).map(p=>option(`${p.position_id} · LED ${p.physical_id??'—'}`,p.position_id)));
        $('toggle-position').disabled=!reviewed;
        $('corner-inputs').replaceChildren();
        g.points.forEach((p,i)=>{const label=document.createElement('label');label.textContent=`${i+1}: x / y`;
            for(const axis of ['x','y']){const input=document.createElement('input');input.type='number';input.step='0.1';input.min=0;input.value=p[axis];input.setAttribute('aria-label',`${i+1} ${axis}`);input.addEventListener('change',()=>{p[axis]=Number(input.value);changed();draw();});label.appendChild(input);}$('corner-inputs').appendChild(label);
        });
        $('extra-list').replaceChildren();
        g.manual_positions.forEach(p=>{const row=document.createElement('div'),label=document.createElement('span'),remove=document.createElement('button');label.textContent=`${t('extra')} ${-p.id}`;row.appendChild(label);
            for(const axis of ['x','y']){const input=document.createElement('input');input.type='number';input.min='0';input.value=p[axis];input.setAttribute('aria-label',`LED ${p.id} ${axis}`);input.addEventListener('change',()=>{p[axis]=Number(input.value);changed();});row.appendChild(input);}
            remove.textContent=t('remove');remove.addEventListener('click',()=>{g.manual_positions=g.manual_positions.filter(other=>other.id!==p.id);g.excluded_position_ids=g.excluded_position_ids.filter(id=>id!==p.id);forgetBores(g.id,new Set([p.id]));changed();renderForm();});row.appendChild(remove);$('extra-list').appendChild(row);
        });
    }
    renderSubgrids();
}
function svgElement(tag,attrs){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [key,value]of Object.entries(attrs))e.setAttribute(key,value);return e;}
function draw(){
    const svg=$('overlay');svg.replaceChildren();const w=initial.coordinate_width,h=initial.coordinate_height;svg.setAttribute('viewBox',`0 0 ${w} ${h}`);
    const r=Math.max(3,w/240),leds=new Map((result?.leds||[]).filter(p=>p.physical_id!==null).map(p=>[p.physical_id,p]));
    const sx=w/layout.coordinate_width,sy=h/layout.coordinate_height,grips=result?.grips||[];
    if(view==='cable')drawCable(svg,r);
    if(view==='cable'&&showLinks)for(const p of grips){if(selectedGrip&&p.key!==selectedGrip)continue;for(const side of ['above','below']){const led=leds.get(p[side]);if(led)svg.appendChild(svgElement('line',{x1:p.x,y1:p.y,x2:led.x,y2:led.y,stroke:side==='above'?'#1985f4':'#f58b12','stroke-width':2,'pointer-events':'none'}));}}
    for(const p of grips){const e=svgElement('circle',{cx:p.x,cy:p.y,r:r*.65,fill:'#42e47b',stroke:p.key===selectedGrip?'#fff':'#18512c','stroke-width':1,'pointer-events':view==='cable'&&showLinks&&cableMode==='pan'?'auto':'none'});const title=svgElement('title',{});title.textContent=gripLabel(p);e.appendChild(title);e.addEventListener('click',event=>{if(pickMode)return;event.stopPropagation();selectedGrip=p.key;showLinks=true;setView('cable');});svg.appendChild(e);}
    for(const p of result?.leds||[]){
        if(view==='leds'&&p.grid_id!==grid()?.id)continue;
        const isSelected=subSelection.has(refKey(p))||edgeSelection.some(q=>sameRef(q,p));
        const e=svgElement('circle',{cx:p.x,cy:p.y,r,fill:p.enabled===false?'#666':p.physical_id===null?'#f7eee0':'#ffc044',stroke:isSelected?'#e137ce':p.physical_id===selectedLED?'#fff':'#553800','stroke-width':isSelected?3:1});
        e.setAttribute('data-led-ref',refKey(p));const title=svgElement('title',{});title.textContent=`LED ${p.physical_id??'—'} · ${p.grid_id} / ${p.position_id}`;e.appendChild(title);
        e.addEventListener('click',event=>{if(pickMode)return;if(view==='cable'&&cableMode!=='pan')return;event.stopPropagation();selectedLED=p.physical_id;if(view==='leds'&&event.shiftKey)toggleBore(p.position_id);buttons();draw();});svg.appendChild(e);
        if(view==='leds'||view==='cable'){const text=svgElement('text',{x:p.x+r+2,y:p.y+4});text.textContent=p.enabled===false?'×':p.physical_id??'·';svg.appendChild(text);}
    }
    if(view==='leds')(pickMode==='corners'?picked:grid()?.points||[]).forEach((p,i)=>{svg.appendChild(svgElement('circle',{cx:p.x*sx,cy:p.y*sy,r:r+3,fill:'none',stroke:'#e54848','stroke-width':2,'pointer-events':'none'}));const label=svgElement('text',{x:p.x*sx+10,y:p.y*sy-10});label.textContent=i+1;svg.appendChild(label);});
    drawSelectionBox(svg);
}
function renderReview(){
    const grips=result?.grips||[];$('grip-select').replaceChildren(option(t('none'),''),...grips.map(p=>option(gripLabel(p),p.key)));$('grip-select').value=selectedGrip||'';
    const selected=grips.find(p=>p.key===selectedGrip);
    for(const side of ['below','above']){const select=$(`${side}-override`);select.replaceChildren(option(t('automatic'),'auto'),option(t('disabled'),'none'));
        (result?.leds||[]).filter(p=>p.physical_id!==null&&p.surface===selected?.surface).forEach(p=>select.appendChild(option(`LED ${p.physical_id}`,refKey(p))));
        const o=layout.overrides[selectedGrip],v=o?.[side];select.value=o&&Object.hasOwn(o,side)?(v===null?'none':typeof v==='object'?refKey(v):refKey(result?.leds.find(p=>p.physical_id===v)||{})):'auto';select.disabled=!selected;
    }
    $('summary').textContent=['below','above'].map(side=>`${t(side)}: `+Object.entries(result?.summary[side]||{}).map(([status,count])=>`${t(status)} ${count}`).join(' · ')).join(' | ');
    $('associations').replaceChildren();
    for(const p of grips){if($('issues-only').checked&&!['below','above'].some(s=>['missing','ambiguous'].includes(p[`${s}_status`])))continue;
        const row=document.createElement('tr');row.className=p.key===selectedGrip?'selected':'';const first=document.createElement('td'),button=document.createElement('button');button.textContent=gripLabel(p);button.addEventListener('click',()=>{selectedGrip=p.key;renderReview();draw();buttons();});first.appendChild(button);row.appendChild(first);
        for(const side of ['below','above']){const cell=document.createElement('td');cell.textContent=`${p[side]??'—'} · ${t(p[`${side}_status`])}`;if(['missing','ambiguous'].includes(p[`${side}_status`]))cell.className='bad';row.appendChild(cell);}$('associations').appendChild(row);
    }
}
function setView(next){
    formToGrid();view=next;cancelPick();cableMode='pan';$('grip-panel').hidden=view!=='grips';$('led-workspace').hidden=view==='grips';$('grid-panel').hidden=view!=='leds';$('cable-panel').hidden=view!=='cable';$('review-panel').hidden=view!=='cable'||!showLinks;
    if(view==='grips'&&!$('grip-frame').getAttribute('src'))$('grip-frame').setAttribute('src',$('grip-frame').getAttribute('data-src'));
    if(view!=='grips')imageZoom.reset();
    renderReview();draw();buttons();
}
async function request(action='calculate'){
    try{
        if(action!=='deactivate')capture();if(pickMode==='corners')throw new Error(t('cornerhelp'));$('editor').inert=true;
        const response=await fetch(api,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({wallid:initial.wallid,action,layout:action==='deactivate'?null:layout})});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail||data));
        active=data.active;
        if(action!=='deactivate'){result=data;reviewed=true;
            // Migrate old numeric exceptions before any cable edits can renumber them.
            for(const o of Object.values(layout.overrides))for(const side of ['above','below'])if(typeof o[side]==='number'){const p=data.leds.find(p=>p.physical_id===o[side]);if(p)o[side]=ledRef(p);}
        }
        if(action==='draft'||action==='activate')dirty=false;
        renderForm();renderReview();draw();buttons();
        message(action==='activate'?t('activated'):action==='draft'?t('saved'):action==='deactivate'?t('legacy'):(data.unconfigured_led_ids.length?`${t('unconfigured')}: ${data.unconfigured_led_ids.join(', ')}`:$('summary').textContent));return true;
    }catch(error){reviewed=false;buttons();message(error.message,true);return false;}finally{$('editor').inert=false;}
}
async function preview(ids,enabled=true){try{$('editor').inert=true;const response=await fetch(previewUrl,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({physical_led_ids:ids,enabled})});const data=await response.json();if(!response.ok||data.status==='partial')throw new Error(data.detail||data.message||`HTTP ${response.status}`);previewActive=enabled;message(data.message);}catch(error){message(error.message,true);}finally{$('editor').inert=false;}}
function cancelPick(){pickMode=null;picked=[];$('cancel-pick').hidden=true;draw();}
function newGrid(source,sourceWidth=initial.coordinate_width,sourceHeight=initial.coordinate_height){
    formToGrid();const g=source?clone(source):{r:2,c:2,points:[],position_start_corner:'top_left',position_direction:'horizontal'};
    const clean=normalizeGrid({...g,id:`led-${Date.now()}-${Math.random().toString(36).slice(2,8)}`,name:`LED ${layout.grids.length+1}`,surface:'1',physical_start:null},layout.grids.length);
    if(source){const sx=layout.coordinate_width/(sourceWidth||initial.coordinate_width),sy=layout.coordinate_height/(sourceHeight||initial.coordinate_height);clean.points.forEach(p=>{p.x*=sx;p.y*=sy;});clean.manual_positions.forEach(p=>{p.x*=sx;p.y*=sy;});}
    layout.grids.push(clean);index=layout.grids.length-1;cancelPick();changed();renderForm();draw();
}
async function deriveGrid(){try{const g=gripGrids[Number($('copy-source').value)];if(!g)throw new Error(t('griphelp'));$('editor').inert=true;
    const response=await fetch(api+'/derive',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({wallid:initial.wallid,grid_id:gridId(g,Number($('copy-source').value)),mode:$('derive-mode').value,offset_rows:Number($('derive-offset').value)})});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));newGrid(data.grid,data.coordinate_width,data.coordinate_height);await request();
}catch(error){message(error.message,true);}finally{$('editor').inert=false;}}
function renderGripSources(){
    $('copy-source').replaceChildren(...gripGrids.map((g,i)=>option(`${t('grid')} ${i+1}`,i)));$('grip-surfaces').replaceChildren();
    gripGrids.forEach((g,i)=>{const label=document.createElement('label'),input=document.createElement('input'),id=gridId(g,i);label.textContent=`${t('grid')} ${i+1}`;input.value=layout.grip_surfaces[id]||'1';input.maxLength=100;input.addEventListener('change',()=>{layout.grip_surfaces[id]=input.value.trim();changed();});label.appendChild(input);$('grip-surfaces').appendChild(label);});
    updateDeriveControls();
}
function updateDeriveControls(){
    const alternating=!!gripGrids[Number($('copy-source').value)]?.alternating;
    $('derive-alternate').disabled=!alternating;
    if(!alternating&&$('derive-mode').value==='alternate')$('derive-mode').value='copy';
    $('derive-offset').disabled=$('derive-mode').value!=='below';
    $('copy-grid').disabled=!gripGrids.length;
}
const unsavedGrips=()=>!!$('grip-frame').contentWindow?.cruxGripUnsaved?.();
async function refreshGrips(){try{if(unsavedGrips())throw new Error(t('savegrips'));const response=await fetch(api+'/data?wallid='+initial.wallid);const data=await response.json();if(!response.ok)throw new Error(data.detail);if(!data.grip_grids.length)throw new Error(t('griphelp'));gripGrids=data.grip_grids;initial.coordinate_width=data.coordinate_width;initial.coordinate_height=data.coordinate_height;
    const ids=new Set(gripGrids.map(gridId));for(const key of Object.keys(layout.grip_surfaces))if(!ids.has(key))delete layout.grip_surfaces[key];
    // The server prunes overrides for deleted grips when saving step 1.
    const keys=new Set(data.grip_keys||[]);for(const key of Object.keys(layout.overrides))if(data.grip_keys&&!keys.has(key))delete layout.overrides[key];
    renderGripSources();reviewed=false;result=null;buttons();draw();message(t('gripsupdated'));return true;
}catch(error){message(error.message,true);return false;}}
function toggleBore(id){const g=grid();if(!g)return;if(g.excluded_position_ids.includes(id))g.excluded_position_ids=g.excluded_position_ids.filter(p=>p!==id);else{g.excluded_position_ids.push(id);forgetBores(g.id,new Set([id]));}changed();}
for(const id of ['grid-select','cable-grid-select'])$(id).addEventListener('change',()=>{formToGrid();index=Number($(id).value);subSelection.clear();cancelPick();renderForm();draw();});
for(const id of ['name','surface','rows','columns','alternating','offset'])$(id).addEventListener('change',()=>{if(['rows','columns','alternating','offset'].includes(id)){forgetBores(grid().id);grid().subgrids=[];grid().excluded_position_ids=[];grid().manual_positions.forEach(p=>p.before_position_id=null);}formToGrid();changed();});
for(const id of ['tolerance','distance'])$(id).addEventListener('input',changed);
$('add-grid').addEventListener('click',()=>newGrid());$('copy-grid').addEventListener('click',deriveGrid);
for(const id of ['copy-source','derive-mode'])$(id).addEventListener('change',updateDeriveControls);
$('delete-grid').addEventListener('click',()=>{if(!window.confirm(t('deleteconfirm')))return;forgetBores(grid().id);layout.grids.splice(index,1);index=Math.max(0,index-1);cancelPick();changed();renderForm();draw();});
$('pick-corners').addEventListener('click',()=>{pickMode='corners';picked=[];$('cancel-pick').hidden=false;message(t('cornerhelp'));draw();});$('cancel-pick').addEventListener('click',cancelPick);
$('add-point').addEventListener('click',()=>{pickMode='extra';$('cancel-pick').hidden=false;message(t('addpoint'));});
$('overlay').addEventListener('click',event=>{if(!pickMode||!grid())return;const rect=$('overlay').getBoundingClientRect(),p={x:Math.round((event.clientX-rect.left)/rect.width*layout.coordinate_width),y:Math.round((event.clientY-rect.top)/rect.height*layout.coordinate_height)};
    if(pickMode==='corners'){picked.push(p);if(picked.length===4){grid().points=clone(picked);cancelPick();changed();renderForm();}}else{const g=grid();g.manual_positions.push({id:Math.min(0,...g.manual_positions.map(p=>p.id))-1,...p,before_position_id:null});changed();renderForm();}draw();});
$('grip-tab').addEventListener('click',()=>setView('grips'));
async function goToLEDs(){if(view==='grips'&&!(await refreshGrips()))return;setView('leds');if(layout.grids.every(g=>g.points.length===4)&&gripGrids.length)await request();}
$('led-tab').addEventListener('click',goToLEDs);$('next-leds').addEventListener('click',goToLEDs);
for(const id of ['cable-tab','next-cable'])$(id).addEventListener('click',async()=>{if(view==='grips'&&!(await refreshGrips()))return;setView('cable');await request();});
$('link-tab').addEventListener('click',()=>{showLinks=!showLinks;setView('cable');});
for(const [id,action]of [['calculate','calculate'],['save-draft','draft'],['activate','activate'],['deactivate','deactivate']])$(id).addEventListener('click',()=>request(action));
$('grip-select').addEventListener('change',()=>{selectedGrip=$('grip-select').value||null;renderReview();draw();buttons();});$('issues-only').addEventListener('change',renderReview);
for(const side of ['below','above'])$(`${side}-override`).addEventListener('change',()=>{if(!selectedGrip)return;const value=$(`${side}-override`).value,o=layout.overrides[selectedGrip]??={};if(value==='auto')delete o[side];else o[side]=value==='none'?null:ledRef(result.leds.find(p=>refKey(p)===value));if(!Object.keys(o).length)delete layout.overrides[selectedGrip];changed();});
$('preview-grip').addEventListener('click',()=>{if(!reviewed)return;const p=result.grips.find(p=>p.key===selectedGrip),sides=$('test-side').value==='both'?['below','above']:[$('test-side').value],ids=[...new Set(sides.map(s=>p?.[s]).filter(id=>id!==null&&id!==undefined))];if(ids.length)preview(ids);else message(t('missing'));});
$('test-led').addEventListener('click',()=>{if(reviewed&&selectedLED!==null)preview([selectedLED]);});
$('position-select').addEventListener('change',()=>{const p=result?.leds.find(p=>p.grid_id===grid()?.id&&p.position_id===Number($('position-select').value));selectedLED=p?.physical_id??null;buttons();draw();});
$('toggle-position').addEventListener('click',()=>{if(!reviewed||!grid())return;toggleBore(Number($('position-select').value));$('toggle-position').disabled=true;});$('stop-preview').addEventListener('click',()=>preview([],false));
window.addEventListener('beforeunload',event=>{if(dirty||unsavedGrips()){event.preventDefault();event.returnValue='';}});window.addEventListener('pagehide',()=>{if(previewActive)navigator.sendBeacon(previewUrl,new Blob([JSON.stringify({physical_led_ids:[],enabled:false})],{type:'application/json'}));});
window.addEventListener('message',async event=>{if(event.origin===window.location.origin&&event.source===$('grip-frame').contentWindow&&event.data?.type==='crux-grips-saved')await refreshGrips();});
window.addEventListener('crux-language-change',()=>{renderForm();renderGripSources();renderReview();buttons();draw();});
$('skipped').value=layout.skipped_physical_ids.join(', ');$('tolerance').value=layout.lateral_tolerance;$('distance').value=layout.max_distance;$('cable-start').value=layout.cable_start;
renderGripSources();renderForm();installCableEvents();
const imageZoom=installImageZoom($('image-viewport'),$('picture'),{canPan:()=>!pickMode&&cableMode==='pan'});
$('wall-image').addEventListener('load',()=>imageZoom.reset());
$('zoom-in').addEventListener('click',()=>imageZoom.zoom(1.4));$('zoom-out').addEventListener('click',()=>imageZoom.zoom(1/1.4));$('zoom-fit').addEventListener('click',()=>imageZoom.reset());
setView(window.location?.hash==='#cable'?'cable':window.location?.hash==='#leds'?'leds':'grips');
if(gripGrids.length)void request('calculate');
