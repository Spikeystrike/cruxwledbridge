// Browser event tests with actual Python cable geometry, not a canned mapping.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),cp=require('node:child_process'),readline=require('node:readline');
const {html,python}=JSON.parse(fs.readFileSync(0,'utf8'));
class Element{
 constructor(tag='div'){this.tagName=tag;this.children=[];this.listeners={};this.style={};this.attrs={};this._value='';this.checked=false;this.disabled=false;this.scrollLeft=0;this.scrollTop=0;}
 set value(v){this._value=String(v);}get value(){return this._value;}
 appendChild(c){this.children.push(c);return c;}append(...c){this.children.push(...c);}replaceChildren(...c){this.children=c;this.value=c[0]?.value??'';}
 setAttribute(k,v){this.attrs[k]=String(v);}getAttribute(k){return this.attrs[k];}addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);}
 async fire(type,event={}){for(const fn of this.listeners[type]||[])await fn({preventDefault(){},stopPropagation(){},stopImmediatePropagation(){},...event});}
 getBoundingClientRect(){return {left:0,top:0,width:250,height:250};}
}
const nodes=new Map([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
for(const [id,value]of [['test-side','below'],['derive-offset','.5'],['derive-mode','copy'],['gap-count','1']])nodes.get(id).value=value;
const document={getElementById:id=>nodes.get(id),createElement:tag=>new Element(tag),createElementNS:(_ns,tag)=>new Element(tag)};
const requests=[],events={},pending=[];let fail=false;
const backend=cp.spawn(python,[require('node:path').join(__dirname,'led_ui_backend.py')],{stdio:['pipe','pipe','inherit']});
readline.createInterface({input:backend.stdout}).on('line',line=>pending.shift()(JSON.parse(line)));
const calculate=body=>new Promise(resolve=>{pending.push(resolve);backend.stdin.write(JSON.stringify(body)+'\n');});
const context=vm.createContext({document,console,window:{location:{origin:'http://test',hash:''},cruxI18n:{t:key=>key},confirm:()=>true,addEventListener(type,fn){events[type]=fn;}},fetch:async(url,options)=>{
 const body=options?JSON.parse(options.body):{refresh:true};requests.push({url,body});if(fail)return {ok:false,json:async()=>({detail:'simulated failure'})};if(url.endsWith('/preview'))return {ok:true,json:async()=>({status:'ok',message:'preview'})};const r=await calculate(body);return {ok:r.ok,json:async()=>r.data};
}});
const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)];vm.runInContext(scripts.at(-1)[1],context);
const run=code=>vm.runInContext(code,context),read=code=>JSON.parse(run(`JSON.stringify(${code})`));
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
const fire=(id,event='click',detail={})=>nodes.get(id).fire(event,detail);
const set=(id,value)=>{nodes.get(id).value=value;};
const pointer=async(type,x,y,id=1)=>{const e={clientX:x/2,clientY:y/2,pointerId:id,button:0};await fire('image-viewport',type,e);await fire('overlay',type,e);};
const clickLED=async(x,y)=>{await pointer('pointerdown',x,y);await pointer('pointerup',x,y);};
(async()=>{
 for(let i=0;i<300&&!read('reviewed');i++)await tick();assert.equal(read('reviewed'),true,nodes.get('status').textContent);
 assert.equal(requests[0].url,'/bridge/ledmapping');assert.equal(requests[0].body.layout.grids[0].surface,'1');
 assert.equal(read('view'),'grips');assert.equal(nodes.get('grip-panel').hidden,false);assert.equal(nodes.get('led-workspace').hidden,true);
 assert.deepEqual(read('parseIDs("1, 4–6 9-10")'),[1,4,5,6,9,10]);assert.throws(()=>run('parseIDs("9-2")'));
 await fire('cable-tab');assert.equal(read('view'),'cable');assert.equal(nodes.get('activate').disabled,false);
 // Absolute skipped IDs get image labels, including IDs beyond visible bores.
 set('skipped','102, 110–112');await fire('skipped','input');assert.equal(nodes.get('activate').disabled,true);await fire('save-draft');
 assert.deepEqual(requests.at(-1).body.layout.skipped_physical_ids,[102,110,111,112]);assert(!requests.some(r=>r.url.endsWith('/preview')));
 assert(nodes.get('overlay').children.some(n=>n.attrs['data-gap-list']==='unplaced_skipped_ids'&&n.textContent.includes('110–112')));
 // Connected endpoints selected by physical IDs highlight in the picture.
 set('gap-from',100);set('gap-to',101);await fire('find-edge');assert.equal(read('edgeSelection.length'),2);
 assert(nodes.get('overlay').children.some(n=>n.attrs.stroke==='#ef2fc4'));
 set('gap-count',2);await fire('insert-gap');assert.deepEqual(read('result.cable_edges[0].skipped_ids'),[101,102]);assert.equal(read('result.leds[1].physical_id'),103);
 assert(nodes.get('overlay').children.some(n=>n.textContent==='+2 [101–102]'));
 await fire('undo-cable');assert.equal(read('result.leds[1].physical_id'),101);assert.deepEqual(read('layout.edge_skips'),[]);
 // Free path supports a swipe with intermediate LEDs, pause/resume, reload and undo.
 await fire('new-path');assert.deepEqual(read('layout.cable_path'),[]);assert.equal(nodes.get('activate').disabled,true);
 await pointer('pointerdown',100,50);await pointer('pointermove',100,350);await pointer('pointerup',100,350);
 assert.deepEqual(read('layout.cable_path.map(p=>p.position_id)'),[0,3,4,7]);
 await fire('draw-path');assert.equal(read('cableMode'),'pan');await fire('save-draft');assert.equal(requests.at(-1).body.layout.cable_path.length,4);
 run('cableUndo=[]');await fire('draw-path');await clickLED(200,350);assert.deepEqual(read('layout.cable_path.map(p=>p.position_id)'),[0,3,4,7,6]);
 await fire('undo-cable');await fire('undo-cable');assert.deepEqual(read('layout.cable_path.map(p=>p.position_id)'),[0,3,4]);
 // A pinch never adds an LED; a canceled swipe rolls back only that gesture.
 await pointer('pointerdown',200,50,1);await pointer('pointerdown',200,150,2);await pointer('pointermove',220,180,2);await pointer('pointerup',220,180,2);await pointer('pointerup',200,50,1);
 assert.deepEqual(read('layout.cable_path.map(p=>p.position_id)'),[0,3,4]);assert(read('imageZoom.scale()')>1);
 await pointer('pointerdown',200,50);await pointer('pointermove',200,150);await pointer('pointercancel',200,150);assert.deepEqual(read('layout.cable_path.map(p=>p.position_id)'),[0,3,4]);
 // Add a gap by tapping its connected endpoints.
 await fire('select-edge');await clickLED(100,50);await clickLED(100,150);assert.equal(read('edgeSelection.length'),2);set('gap-count',1);await fire('insert-gap');assert.equal(read('layout.edge_skips[0].count'),1);
 // Subgrid selection by rectangle gives each section an independent pattern.
 await fire('use-patterns');await fire('select-subgrid');await pointer('pointerdown',90,40);await pointer('pointermove',110,360);await pointer('pointerup',110,360);
 assert.equal(read('subSelection.size'),4);await fire('create-subgrid');assert.deepEqual(read('layout.grids[0].subgrids[0].position_ids'),[0,3,4,7]);assert.deepEqual(read('result.cable_order.slice(0,4).map(p=>p.position_id)'),[0,3,4,7]);
 await fire('undo-cable');assert.equal(read('layout.grids[0].subgrids.length'),0);
 // Exceptions are attached to stable bores even when numbering changes.
 await fire('link-tab');set('grip-select','grips:r0c0');await fire('grip-select','change');set('below-override','none');await fire('below-override','change');assert.deepEqual(read('layout.overrides'),{'grips:r0c0':{below:null}});set('below-override','auto');await fire('below-override','change');await fire('calculate');await fire('preview-grip');assert.deepEqual(requests.at(-1).body,{physical_led_ids:[104],enabled:true});await fire('stop-preview');
 // Step 2 derives geometry using the real perspective transform.
 await fire('led-tab');const before=read('initial.grip_grids');set('derive-mode','below');set('copy-source',0);await fire('copy-grid');assert.deepEqual(read('initial.grip_grids'),before);assert.equal(read('layout.grids[1].points[0].y'),150);
 set('position-select',1);await fire('toggle-position');assert.deepEqual(read('layout.grids[1].excluded_position_ids'),[1]);
 await fire('add-point');await fire('overlay','click',{clientX:70,clientY:90});assert.deepEqual(read('layout.grids[1].manual_positions'),[{id:-1,x:140,y:180,before_position_id:null}]);await fire('cancel-pick');
 fail=true;await fire('save-draft');assert.equal(read('layout.grids[1].manual_positions.length'),1);assert.equal(nodes.get('status').textContent,'simulated failure');assert.equal(nodes.get('editor').inert,false);fail=false;
 // Saving/refreshing grips must not replace unsaved LED changes.
 await fire('grip-tab');await fire('next-leds');assert.equal(read('layout.grids[1].manual_positions.length'),1);
 await fire('add-grid');await fire('pick-corners');for(const [clientX,clientY]of [[10,10],[50,10],[50,50],[10,50]])await fire('overlay','click',{clientX,clientY});assert.deepEqual(read('grid().points'),[{x:20,y:20},{x:100,y:20},{x:100,y:100},{x:20,y:100}]);
 const scale=read('imageZoom.scale()');await fire('zoom-in');assert(read('imageZoom.scale()')>scale);await fire('zoom-fit');assert.equal(read('imageZoom.scale()'),1);
 console.log('Independent LED UI passed');
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>backend.stdin.end());
