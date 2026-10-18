// Run the generated editor against a minimal DOM and mocked HTTP responses.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {html, result} = JSON.parse(fs.readFileSync(0, 'utf8'));
class Element {
    constructor(tag='div') { this.tagName=tag; this.children=[]; this.listeners={}; this.style={}; this.attrs={}; this._value=''; this.checked=false; this.disabled=false; }
    set value(value) { this._value=String(value); } get value() { return this._value; }
    appendChild(child) { this.children.push(child); return child; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children=children; this.value=children[0]?.value ?? ''; }
    setAttribute(key,value) { this.attrs[key]=String(value); }
    getAttribute(key) { return this.attrs[key]; }
    addEventListener(type,fn) { (this.listeners[type]??=[]).push(fn); }
    async fire(type,event={}) { for (const fn of this.listeners[type]||[]) await fn({preventDefault(){},stopPropagation(){},...event}); }
    getBoundingClientRect() { return {left:0,top:0,width:250,height:250}; }
}
const nodes = new Map([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
nodes.get('shift').value='0.5';
nodes.get('test-side').value='below';
const document = {getElementById:id=>nodes.get(id),createElement:tag=>new Element(tag),createElementNS:(_ns,tag)=>new Element(tag)};
const requests=[];
let fail=false;
const context = vm.createContext({document,console,window:{cruxI18n:{t:key=>key},confirm:()=>true,addEventListener(){}},
    fetch:async(url,options)=>{
        const body=JSON.parse(options.body);requests.push({url,body});
        if(fail) return {ok:false,json:async()=>({detail:'simulated failure'})};
        if(url.endsWith('/preview')) return {ok:true,json:async()=>({status:'ok',message:'preview'})};
        return {ok:true,json:async()=>({...result,active:body.action==='activate'})};
    }});
const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)];
vm.runInContext(scripts.at(-1)[1],context);
const run=code=>vm.runInContext(code,context);
const read=code=>JSON.parse(run(`JSON.stringify(${code})`));
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
    await tick();
    assert.equal(requests[0].url,'/bridge/ledmapping');
    assert.equal(requests[0].body.action,'calculate');
    assert.equal(requests[0].body.layout.grids[0].surface,'1');
    assert.equal(nodes.get('activate').disabled,false);
    assert.equal(nodes.get('state').textContent,'legacy');
    assert.deepEqual(read('parseIDs("1, 4–6 9-10")'),[1,4,5,6,9,10]);
    assert.throws(()=>run('parseIDs("3-no")'));
    assert.throws(()=>run('parseIDs("9-2")'));
    // Known hidden cable LEDs are stored, without contacting WLED.
    nodes.get('skipped').value='102, 110–112';
    await nodes.get('skipped').fire('input');
    assert.equal(nodes.get('activate').disabled,true);
    await nodes.get('save-draft').fire('click');
    assert.deepEqual(requests.at(-1).body.layout.skipped_physical_ids,[102,110,111,112]);
    assert.equal(requests.at(-1).body.action,'draft');
    assert.equal(nodes.get('state').textContent,'legacy');
    assert(!requests.some(r=>r.url.endsWith('/preview')));
    // Manual override: explicit no LED differs from automatic.
    await nodes.get('link-tab').fire('click');
    nodes.get('grip-select').value='grips:r0c0';
    await nodes.get('grip-select').fire('change');
    nodes.get('below-override').value='none';
    await nodes.get('below-override').fire('change');
    assert.deepEqual(read('layout.overrides'),{'grips:r0c0':{below:null}});
    assert.equal(nodes.get('preview-grip').disabled,true);
    nodes.get('below-override').value='auto';
    await nodes.get('below-override').fire('change');
    assert.deepEqual(read('layout.overrides'),{});
    await nodes.get('calculate').fire('click');
    await nodes.get('preview-grip').fire('click');
    assert.deepEqual(requests.at(-1).body,{physical_led_ids:[104],enabled:true});
    await nodes.get('stop-preview').fire('click');
    assert.deepEqual(requests.at(-1).body,{physical_led_ids:[],enabled:false});
    // Perspective-adjusted initial shift moves LED geometry, never grip grids.
    await nodes.get('led-tab').fire('click');
    const before=read('initial.grip_grids');
    await nodes.get('shift-grid').fire('click');
    assert.deepEqual(read('initial.grip_grids'),before);
    assert.equal(read('layout.grids[0].points[0].y'),100);
    assert.equal(nodes.get('activate').disabled,true);
    await nodes.get('calculate').fire('click');
    // A touch-accessible position control excludes a visible bore.
    nodes.get('position-select').value='1';
    await nodes.get('toggle-position').fire('click');
    assert.deepEqual(read('layout.grids[0].excluded_position_ids'),[1]);
    // Adding a physical LED works independently from generated grid holes.
    await nodes.get('add-point').fire('click');
    await nodes.get('overlay').fire('click',{clientX:70,clientY:90});
    assert.deepEqual(read('layout.grids[0].manual_positions'),[{id:-1,x:140,y:180,before_position_id:null}]);
    await nodes.get('cancel-pick').fire('click');
    // Failed saving retains all edits and does not change active configuration.
    fail=true;
    await nodes.get('save-draft').fire('click');
    assert.equal(read('layout.grids[0].manual_positions.length'),1);
    assert.equal(nodes.get('status').textContent,'simulated failure');
    assert.equal(nodes.get('editor').inert,false);
    assert.equal(read('active'),false);
    fail=false;
    await nodes.get('calculate').fire('click');
    await nodes.get('activate').fire('click');
    assert.equal(requests.at(-1).body.action,'activate');
    assert.equal(read('active'),true);
    assert.equal(nodes.get('state').textContent,'active');
    // A new grid can choose independent corners/counts, including extra rows.
    await nodes.get('add-grid').fire('click');
    await nodes.get('pick-corners').fire('click');
    for(const [clientX,clientY] of [[10,10],[50,10],[50,50],[10,50]]) await nodes.get('overlay').fire('click',{clientX,clientY});
    assert.deepEqual(read('layout.grids[1].points'),[{x:20,y:20},{x:100,y:20},{x:100,y:100},{x:20,y:100}]);
    assert.equal(read('pickMode'),null);
    console.log('Independent LED UI passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
