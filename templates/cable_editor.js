// Cable editing uses stable bore references; physical numbers are a result.
let cableMode='pan', edgeSelection=[], subSelection=new Set(), cableUndo=[], cableGesture=null;
const ledRef=p=>({grid_id:p.grid_id,position_id:p.position_id});
const refKey=p=>JSON.stringify([p.grid_id,p.position_id]);
const sameRef=(a,b)=>!!a&&!!b&&a.grid_id===b.grid_id&&a.position_id===b.position_id;
function wiringSnapshot(){return clone({path:layout.cable_path,start:layout.cable_start,gaps:layout.edge_skips,skips:layout.skipped_physical_ids,grids:layout.grids.map(g=>({id:g.id,led_start_corner:g.led_start_corner,led_direction:g.led_direction,physical_start:g.physical_start,subgrids:g.subgrids}))});}
function rememberCable(){cableUndo.push(wiringSnapshot());if(cableUndo.length>1000)cableUndo.shift();}
function restoreWiring(s){layout.cable_path=s.path;layout.cable_start=s.start;layout.edge_skips=s.gaps;layout.skipped_physical_ids=s.skips;const grids=new Map(layout.grids.map(g=>[g.id,g]));layout.grids=s.grids.map(g=>Object.assign(grids.get(g.id),g));$('skipped').value=s.skips.join(', ');$('cable-start').value=s.start;}
function patternFor(g,points,corner,direction){
    const regular=points.filter(p=>p.row!==null), horizontal=direction==='horizontal', stripe=horizontal?'row':'column', along=horizontal?'column':'row';
    const startsTop=corner.startsWith('top_'),startsLeft=corner.endsWith('_left'),stripes=[...new Set(regular.map(p=>p[stripe]))].sort((a,b)=>(horizontal?startsTop:startsLeft)?a-b:b-a);
    const order=[];stripes.forEach((s,i)=>{const ascending=(horizontal?startsLeft:startsTop)!==!!(i%2);order.push(...regular.filter(p=>p[stripe]===s).sort((a,b)=>ascending?a[along]-b[along]:b[along]-a[along]));});
    for(const extra of g.manual_positions){const p=points.find(p=>p.position_id===extra.id);if(!p)continue;const at=order.findIndex(p=>p.position_id===extra.before_position_id);order.splice(at<0?order.length:at,0,p);}
    return order.filter(p=>p.enabled!==false).map(ledRef);
}
function patternOrder(){
    const order=[];
    for(const g of layout.grids){const group=(result?.leds||[]).filter(p=>p.grid_id===g.id),claimed=new Set();
        for(const sub of g.subgrids){const ids=new Set(sub.position_ids);order.push(...patternFor(g,group.filter(p=>ids.has(p.position_id)),sub.start_corner,sub.direction));ids.forEach(id=>claimed.add(id));}
        order.push(...patternFor(g,group.filter(p=>!claimed.has(p.position_id)),g.led_start_corner,g.led_direction));
    }return order;
}
function pruneEdges(order=layout.cable_path??patternOrder()){
    const adjacent=new Set(order.slice(1).map((p,i)=>refKey(order[i])+'>'+refKey(p)));
    layout.edge_skips=layout.edge_skips.filter(g=>adjacent.has(refKey(g.source)+'>'+refKey(g.target)));
    if(edgeSelection.length===2&&!adjacent.has(refKey(edgeSelection[0])+'>'+refKey(edgeSelection[1])))edgeSelection=[];
}
function forgetBores(gridId,ids=null){
    cableUndo=[];const removed=p=>p.grid_id===gridId&&(!ids||ids.has(p.position_id));
    if(layout.cable_path)layout.cable_path=layout.cable_path.filter(p=>!removed(p));
    for(const g of layout.grids)if(g.id===gridId)g.subgrids=g.subgrids.map(s=>({...s,position_ids:ids?s.position_ids.filter(id=>!ids.has(id)):[]})).filter(s=>s.position_ids.length);
    layout.edge_skips=layout.edge_skips.filter(g=>!removed(g.source)&&!removed(g.target));pruneEdges();
    for(const [key,o]of Object.entries(layout.overrides)){for(const side of ['above','below'])if(o[side]&&typeof o[side]==='object'&&removed(o[side]))delete o[side];if(!Object.keys(o).length)delete layout.overrides[key];}
}
function syncCablePreview(){
    if(!result)return;
    const order=layout.cable_path??patternOrder(),points=new Map(result.leds.map(p=>[refKey(p),p])),skipped=new Set(layout.skipped_physical_ids),represented=new Set();
    for(const p of result.leds)p.physical_id=null;
    const starts=new Map();if(layout.cable_path!==null){if(order.length)starts.set(refKey(order[0]),layout.cable_start);const entered=new Set(order.length?[order[0].grid_id]:[]);for(const p of order){const g=layout.grids.find(g=>g.id===p.grid_id);if(!entered.has(p.grid_id)&&g?.physical_start!==null&&g?.physical_start!==undefined)starts.set(refKey(p),g.physical_start);entered.add(p.grid_id);}}else for(const g of layout.grids){const first=order.find(p=>p.grid_id===g.id);if(first&&g.physical_start!==null&&g.physical_start!==undefined)starts.set(refKey(first),g.physical_start);}
    const gaps=new Map(layout.edge_skips.map(g=>[refKey(g.source)+'>'+refKey(g.target),g.count]));let next=0,previous=null;const edges=[];let leading=[];
    for(const ref of order){const p=points.get(refKey(ref));if(!p||p.enabled===false)continue;next=starts.get(refKey(ref))??next;const count=previous?(gaps.get(refKey(previous)+'>'+refKey(ref))||0):0,ids=[];for(let i=0;i<count;i++)ids.push(next++);while(skipped.has(next))ids.push(next++);p.physical_id=next++;
        if(previous){const before=points.get(refKey(previous)).physical_id;for(const id of skipped)if(id>before&&id<p.physical_id&&!ids.includes(id))ids.push(id);ids.sort((a,b)=>a-b);edges.push({source:ledRef(previous),target:ledRef(ref),skipped_ids:ids,inserted_count:count});}else leading=ids;
        ids.forEach(id=>represented.add(id));previous=ref;
    }
    result.cable_order=clone(order);result.cable_edges=edges;result.leading_skipped_ids=leading;result.unplaced_skipped_ids=[...skipped].filter(id=>!represented.has(id));result.unwired_count=result.leds.filter(p=>p.enabled!==false&&p.physical_id===null).length;
}
function cableChanged(){changed();syncCablePreview();draw();renderCableTools();}
function renderCableTools(){
    $('draw-path').textContent=t(cableMode==='draw'?'pausepath':'continuepath');$('draw-path').setAttribute('aria-pressed',String(cableMode==='draw'));
    $('select-subgrid').setAttribute('aria-pressed',String(cableMode==='subgrid'));$('select-edge').setAttribute('aria-pressed',String(cableMode==='edge'));$('pan-image').setAttribute('aria-pressed',String(cableMode==='pan'));
    $('use-patterns').setAttribute('aria-pressed',String(layout.cable_path===null));$('pattern-controls').open=layout.cable_path===null;
    $('pattern-fields').disabled=layout.cable_path!==null;
    $('undo-cable').disabled=!cableUndo.length&&!layout.cable_path?.length;
    $('cable-status').textContent=`${result?.cable_order?.length||0} LED · ${result?.unwired_count||0} ${t('unwired')}`;
    const points=new Map((result?.leds||[]).map(p=>[refKey(p),p]));
    if(edgeSelection.length===2){const a=points.get(refKey(edgeSelection[0])),b=points.get(refKey(edgeSelection[1]));$('gap-from').value=a?.physical_id??'';$('gap-to').value=b?.physical_id??'';$('edge-status').textContent=`LED ${a?.physical_id??'—'} → LED ${b?.physical_id??'—'}`;}else $('edge-status').textContent=edgeSelection.length?'LED …':'';
}
function renderSubgrids(){
    $('subgrid-list').replaceChildren();const g=grid();if(!g)return;
    g.subgrids.forEach((s,i)=>{const row=document.createElement('div'),label=document.createElement('button');label.textContent=`${i+1}. ${s.name||t('subgrid')} (${s.position_ids.length} LED)`;label.addEventListener('click',()=>{subSelection=new Set(s.position_ids.map(id=>refKey({grid_id:g.id,position_id:id})));cableMode='pan';renderCableTools();draw();});row.appendChild(label);
        for(const [field,values]of [['start_corner',['bottom_left','bottom_right','top_left','top_right']],['direction',['vertical','horizontal']]]){const select=document.createElement('select');select.setAttribute('aria-label',t(field==='direction'?'path':'start'));select.replaceChildren(...values.map(v=>option(t(v),v)));select.value=s[field];select.addEventListener('change',async()=>{rememberCable();s[field]=select.value;layout.cable_path=null;pruneEdges();cableChanged();await request();});row.appendChild(select);}
        for(const [labelText,delta]of [['↑',-1],['↓',1]]){const b=document.createElement('button');b.textContent=labelText;b.setAttribute('aria-label',t(delta<0?'earlier':'later'));b.disabled=i+delta<0||i+delta>=g.subgrids.length;b.addEventListener('click',async()=>{rememberCable();[g.subgrids[i],g.subgrids[i+delta]]=[g.subgrids[i+delta],g.subgrids[i]];pruneEdges();cableChanged();await request();});row.appendChild(b);}
        const remove=document.createElement('button');remove.textContent=t('remove');remove.addEventListener('click',async()=>{rememberCable();g.subgrids.splice(i,1);pruneEdges();cableChanged();await request();});row.appendChild(remove);$('subgrid-list').appendChild(row);
    });
}
function compactIDs(ids){const sorted=[...new Set(ids)].sort((a,b)=>a-b),parts=[];for(let i=0;i<sorted.length;i++){const first=sorted[i];let last=first;while(sorted[i+1]===last+1)last=sorted[++i];parts.push(first===last?`${first}`:`${first}–${last}`);}return parts.join(', ');}
function drawCable(svg,r){
    const points=new Map((result?.leds||[]).map(p=>[refKey(p),p]));
    for(const edge of result?.cable_edges||[]){const a=points.get(refKey(edge.source)),b=points.get(refKey(edge.target));if(!a||!b)continue;
        const selected=edgeSelection.length===2&&sameRef(edge.source,edgeSelection[0])&&sameRef(edge.target,edgeSelection[1]);
        svg.appendChild(svgElement('line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:selected?'#ef2fc4':edge.skipped_ids.length?'#e94c3b':'#50adff','stroke-width':selected?4:2,'stroke-dasharray':edge.skipped_ids.length?'6 4':'none','pointer-events':'none'}));
        const dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy);if(d>r*4){const x=a.x+dx*.62,y=a.y+dy*.62,ux=dx/d,uy=dy/d;svg.appendChild(svgElement('path',{d:`M ${x-ux*r-uy*r*.6} ${y-uy*r+ux*r*.6} L ${x} ${y} L ${x-ux*r+uy*r*.6} ${y-uy*r-ux*r*.6}`,fill:'none',stroke:'#50adff','stroke-width':2,'pointer-events':'none'}));}
        if(edge.skipped_ids.length){const x=(a.x+b.x)/2,y=(a.y+b.y)/2;svg.appendChild(svgElement('rect',{x:x-r,y:y-r,width:r*2,height:r*2,fill:'#f65a43',stroke:'#fff',transform:`rotate(45 ${x} ${y})`,'pointer-events':'none'}));const label=svgElement('text',{x:x+r+2,y:y-r-2});label.textContent=`+${edge.skipped_ids.length} [${compactIDs(edge.skipped_ids)}]`;svg.appendChild(label);}
    }
    let y=22;for(const [key,label]of [['leading_skipped_ids','leading'],['unplaced_skipped_ids','unplaced']]){const ids=result?.[key]||[];if(!ids.length)continue;const text=svgElement('text',{x:12,y,'data-gap-list':key});text.textContent=`${t(label)}: ${compactIDs(ids)}`;svg.appendChild(text);y+=22;}
}
function drawSelectionBox(svg){if(cableGesture?.mode!=='subgrid'||!cableGesture.last)return;const a=cableGesture.start,b=cableGesture.last;svg.appendChild(svgElement('rect',{x:Math.min(a.x,b.x),y:Math.min(a.y,b.y),width:Math.abs(b.x-a.x),height:Math.abs(b.y-a.y),fill:'#ba55c933',stroke:'#e137ce','stroke-width':2,'pointer-events':'none'}));}
function chooseEdge(a,b){const order=result?.cable_order||[];let i=order.findIndex(p=>sameRef(p,a)),j=order.findIndex(p=>sameRef(p,b));if(i<0||j<0||Math.abs(i-j)!==1){message(t('notadjacent'),true);return false;}edgeSelection=i<j?[ledRef(a),ledRef(b)]:[ledRef(b),ledRef(a)];renderCableTools();draw();return true;}
function distanceToSegment(p,a,b){const dx=b.x-a.x,dy=b.y-a.y,den=dx*dx+dy*dy,u=den?Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/den)):0;return {distance:Math.hypot(p.x-a.x-u*dx,p.y-a.y-u*dy),u};}
function imagePoint(event){const r=$('overlay').getBoundingClientRect();return {x:(event.clientX-r.left)/r.width*initial.coordinate_width,y:(event.clientY-r.top)/r.height*initial.coordinate_height};}
function hitRadius(){const rect=$('overlay').getBoundingClientRect();return Math.max(initial.coordinate_width/240,10*initial.coordinate_width/rect.width);}
function hitLED(p){return (result?.leds||[]).filter(q=>q.enabled!==false).map(q=>({q,d:Math.hypot(q.x-p.x,q.y-p.y)})).filter(q=>q.d<=hitRadius()).sort((a,b)=>a.d-b.d)[0]?.q;}
function appendCableLED(p){if(!p||layout.cable_path===null||layout.cable_path.some(q=>sameRef(p,q)))return;rememberCable();layout.cable_path.push(ledRef(p));cableChanged();}
function traceSegment(a,b){const seen=new Set((layout.cable_path||[]).map(refKey)),hits=(result?.leds||[]).filter(p=>p.enabled!==false&&!seen.has(refKey(p))).map(p=>({p,...distanceToSegment(p,a,b)})).filter(p=>p.distance<=hitRadius()).sort((p,q)=>p.u-q.u||p.distance-q.distance);for(const {p}of hits)appendCableLED(p);}
function startDrawing(){if(!result)return;if(layout.cable_path===null){rememberCable();layout.cable_path=clone(result.cable_order);layout.cable_start=result.leds.find(p=>sameRef(p,layout.cable_path[0]))?.physical_id??0;$('cable-start').value=layout.cable_start;changed();}cableMode='draw';showLinks=false;$('review-panel').hidden=true;renderCableTools();draw();}
function cancelCableGesture(){if(cableGesture?.snapshot){restoreWiring(cableGesture.snapshot);cableUndo.length=cableGesture.undoLength;syncCablePreview();}cableGesture=null;draw();}
function installCableEvents(){
    $('new-path').addEventListener('click',async()=>{if(!result)return;rememberCable();layout.cable_path=[];layout.edge_skips=[];edgeSelection=[];cableChanged();startDrawing();await request();});
    $('draw-path').addEventListener('click',async()=>{if(cableMode==='draw'){cableMode='pan';renderCableTools();await request();}else startDrawing();});
    $('pan-image').addEventListener('click',()=>{cableMode='pan';cableGesture=null;renderCableTools();draw();});
    $('use-patterns').addEventListener('click',async()=>{rememberCable();layout.cable_path=null;pruneEdges();cableMode='pan';cableChanged();await request();});
    $('undo-cable').addEventListener('click',async()=>{if(cableUndo.length)restoreWiring(cableUndo.pop());else if(layout.cable_path?.length){layout.cable_path.pop();pruneEdges();}else return;edgeSelection=[];cableChanged();renderForm();await request();});
    for(const id of ['start','path','physical-start','cable-start'])$(id).addEventListener('change',async()=>{rememberCable();formToGrid();layout.cable_start=Number($('cable-start').value);if(id!=='cable-start')layout.cable_path=null;pruneEdges();cableChanged();await request();});
    $('skipped').addEventListener('change',async()=>{try{const ids=parseIDs($('skipped').value);rememberCable();layout.skipped_physical_ids=ids;cableChanged();await request();}catch(error){message(error.message,true);}});
    $('skipped').addEventListener('input',changed);
    for(const [id,delta]of [['earlier',-1],['later',1]])$(id).addEventListener('click',async()=>{rememberCable();formToGrid();const target=index+delta;[layout.grids[index],layout.grids[target]]=[layout.grids[target],layout.grids[index]];index=target;layout.cable_path=null;pruneEdges();cableChanged();renderForm();await request();});
    $('select-subgrid').addEventListener('click',()=>{cableMode=cableMode==='subgrid'?'pan':'subgrid';renderCableTools();draw();});$('clear-selection').addEventListener('click',()=>{subSelection.clear();draw();});
    $('create-subgrid').addEventListener('click',async()=>{const g=grid(),ids=(result?.leds||[]).filter(p=>p.grid_id===g?.id&&subSelection.has(refKey(p))).map(p=>p.position_id);if(!ids.length){message(t('selectfirst'),true);return;}if(g.subgrids.some(s=>s.position_ids.some(id=>ids.includes(id)))){message(t('suboverlap'),true);return;}rememberCable();g.subgrids.push({id:`sub-${Date.now()}-${Math.random().toString(36).slice(2,6)}`,name:$('subgrid-name').value||`${t('subgrid')} ${g.subgrids.length+1}`,position_ids:ids,start_corner:$('start').value,direction:$('path').value});layout.cable_path=null;pruneEdges();subSelection.clear();cableMode='pan';cableChanged();await request();});
    $('select-edge').addEventListener('click',()=>{cableMode='edge';edgeSelection=[];renderCableTools();draw();});
    $('find-edge').addEventListener('click',()=>{const a=result?.leds.find(p=>p.physical_id===Number($('gap-from').value)),b=result?.leds.find(p=>p.physical_id===Number($('gap-to').value));if($('gap-from').value===''||$('gap-to').value===''||!a||!b){message(t('notadjacent'),true);return;}chooseEdge(a,b);});
    $('insert-gap').addEventListener('click',async()=>{if(edgeSelection.length!==2){message(t('notadjacent'),true);return;}const count=Number($('gap-count').value);if(!Number.isInteger(count)||count<1||count>10000){message(t('invalidnumbers'),true);return;}const gap=layout.edge_skips.find(g=>sameRef(g.source,edgeSelection[0])&&sameRef(g.target,edgeSelection[1]));if((gap?.count||0)+count>10000){message(t('invalidnumbers'),true);return;}rememberCable();if(gap)gap.count+=count;else layout.edge_skips.push({source:ledRef(edgeSelection[0]),target:ledRef(edgeSelection[1]),count});cableChanged();await request();});
    $('remove-gap').addEventListener('click',async()=>{if(edgeSelection.length!==2)return;rememberCable();layout.edge_skips=layout.edge_skips.filter(g=>!sameRef(g.source,edgeSelection[0])||!sameRef(g.target,edgeSelection[1]));cableChanged();await request();});
    const svg=$('overlay');
    svg.addEventListener('pointerdown',event=>{
        if(view!=='cable'||cableMode==='pan'||pickMode||!result)return;
        if(imageZoom.isPinching()){cancelCableGesture();return;}if(cableGesture)return;
        event.preventDefault();svg.setPointerCapture?.(event.pointerId);const p=imagePoint(event);
        cableGesture={id:event.pointerId,mode:cableMode,start:p,last:p,moved:false,snapshot:cableMode==='draw'?wiringSnapshot():null,undoLength:cableUndo.length};
    });
    svg.addEventListener('pointermove',event=>{
        if(!cableGesture||event.pointerId!==cableGesture.id)return;if(imageZoom.isPinching()){cancelCableGesture();return;}event.preventDefault();const p=imagePoint(event),g=cableGesture;
        if(Math.hypot(p.x-g.start.x,p.y-g.start.y)>hitRadius()*.3)g.moved=true;
        if(g.mode==='draw'&&g.moved)traceSegment(g.last,p);g.last=p;if(g.mode==='subgrid')draw();
    });
    const finish=async event=>{const g=cableGesture;if(!g||event.pointerId!==g.id)return;event.preventDefault();const p=imagePoint(event);cableGesture=null;
        if(g.mode==='draw'){if(g.moved)traceSegment(g.last,p);else appendCableLED(hitLED(p));await request();}
        else if(g.mode==='subgrid'){if(g.moved){for(const led of result.leds)if(led.grid_id===grid()?.id&&led.enabled!==false&&led.x>=Math.min(g.start.x,p.x)&&led.x<=Math.max(g.start.x,p.x)&&led.y>=Math.min(g.start.y,p.y)&&led.y<=Math.max(g.start.y,p.y))subSelection.add(refKey(led));}else{const led=hitLED(p);if(led&&led.grid_id===grid()?.id){const key=refKey(led);if(subSelection.has(key))subSelection.delete(key);else subSelection.add(key);}}draw();}
        else if(g.mode==='edge'){const led=hitLED(p);if(led){if(edgeSelection.length!==1)edgeSelection=[ledRef(led)];else chooseEdge(edgeSelection[0],led);}else{const points=new Map(result.leds.map(p=>[refKey(p),p])),edge=result.cable_edges.map(e=>({e,...distanceToSegment(p,points.get(refKey(e.source)),points.get(refKey(e.target)))})).filter(e=>e.distance<=hitRadius()).sort((a,b)=>a.distance-b.distance)[0]?.e;if(edge)chooseEdge(edge.source,edge.target);}renderCableTools();draw();}
    };
    svg.addEventListener('pointerup',finish);svg.addEventListener('pointercancel',()=>cancelCableGesture());
}
