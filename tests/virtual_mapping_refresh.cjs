const assert=require('node:assert/strict'), fs=require('node:fs'), vm=require('node:vm');
const html=fs.readFileSync(0,'utf8');
class Element {
    constructor(){this.children=[];this.listeners={};this.style={};this._value='';this.classList={toggle(){}};this.complete=true;this.naturalWidth=500;this.naturalHeight=500;}
    set value(v){this._value=String(v);} get value(){return this._value;}
    appendChild(c){c.parent=this;this.children.push(c);} replaceChildren(...c){this.children=c;}
    addEventListener(k,f){(this.listeners[k]??=[]).push(f);}
    querySelectorAll(){return this.children;} remove(){if(this.parent)this.parent.children=this.parent.children.filter(c=>c!==this);}
    getBoundingClientRect(){return {left:0,top:0,width:500,height:500};}
}
const nodes=new Map([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
nodes.get('board-type').value='mini';
const pending=[];
const context=vm.createContext({document:{getElementById:id=>nodes.get(id),createElement:()=>new Element()},
    window:{cruxI18n:{t:k=>k},addEventListener(){}}, console,
    fetch:(url,options)=>new Promise(resolve=>pending.push({url,body:JSON.parse(options.body),resolve}))});
vm.runInContext([...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].at(-1)[1],context);
const run=s=>vm.runInContext(s,context), read=s=>JSON.parse(run(`JSON.stringify(${s})`));
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const match=ids=>({virtual_position_id:0,virtual_x:100,virtual_y:100,source_x:100,source_y:100,logical_led_id:0,physical_led_ids:ids,below_status:'automatic'});
context.sample={id:'saved',name:'Saved board',board_type:'mini',setup:'mini_2020',mapping:{r:12,c:11,points:[{x:0,y:0},{x:500,y:0},{x:500,y:500},{x:0,y:500}],matches:[match([999])],physical_led_ids:[999]}};
(async()=>{
    const loading=run('loadSavedMapping(sample)'); await tick();
    assert.equal(pending.length,1);
    assert.deepEqual(read('physicalIds'),[]);
    assert.equal(nodes.get('physical-led-output').value,'');
    assert.equal(nodes.get('preview-button').disabled,true);
    assert.equal(pending[0].url,'/bridge/virtualmapping/calculate');
    pending.shift().resolve({ok:true,json:async()=>({matches:[match([]),{...match([104]),virtual_position_id:1}],physical_led_ids:[104]})});
    await loading;
    assert.deepEqual(read('physicalIds'),[104]);
    assert.equal(nodes.get('physical-led-output').value,', 104');
    assert.equal(context.sample.mapping.physical_led_ids[0],999); // Stored snapshot unchanged.
    // Geometry changes while a refresh is pending invalidate its response.
    const stale=run('loadSavedMapping(sample)'); await tick();
    await run('clearResult()');
    pending.shift().resolve({ok:true,json:async()=>({matches:[match([999])],physical_led_ids:[999]})});
    await stale;
    assert.deepEqual(read('physicalIds'),[]);
    // Failures never expose the old saved LEDs for physical preview.
    const failure=run('loadSavedMapping(sample)');await tick();
    pending.shift().resolve({ok:false,status:400,json:async()=>({detail:'invalid layout'})});
    await failure;
    assert.equal(nodes.get('preview-button').disabled,true);
    assert.deepEqual(read('physicalIds'),[]);
    console.log('Saved MoonBoard refresh passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
