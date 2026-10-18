'use strict';
const initial = __DATA__;
const api = __API__, previewUrl = __PREVIEW__;
const $ = id => document.getElementById(id);
const t = key => window.cruxI18n.t(key);
const clone = value => JSON.parse(JSON.stringify(value));
let layout = clone(initial.layout), active = initial.active;
layout.overrides ??= {}; layout.grip_surfaces ??= {};
layout.skipped_physical_ids ??= []; layout.lateral_tolerance ??= 0.35; layout.max_distance ??= 0.9;
layout.grids.forEach((g,i) => {
    g.name ??= `LED ${i+1}`; g.surface ??= '1'; g.alternating ??= false;
    g.alternating_start_column ??= 0; g.led_start_corner ??= 'bottom_left';
    g.led_direction ??= 'vertical'; g.manual_positions ??= []; g.excluded_position_ids ??= [];
});
let index = 0, result = null, reviewed = false, dirty = false, view = 'leds';
let selectedGrip = null, selectedLED = null, pickMode = null, picked = [], previewActive = false;
const gripGrids = initial.grip_grids;
const gridId = (g, i) => g.id || `grid-${i + 1}`;
const option = (text, value) => { const o = document.createElement('option'); o.textContent = text; o.value = value; return o; };
const grid = () => layout.grids[index];
const gripLabel = p => `${t('grid')} ${p.grid_index+1} · ${p.row === null ? `${t('extra')} ${-p.position_id}` : `${t('row')} ${p.row+1}, ${t('col')} ${p.column+1}`}`;
function message(text, error = false) { $('status').textContent = text; $('status').className = error ? 'error' : ''; }
function buttons() {
    $('activate').disabled = !reviewed || !result?.grips.some(p => p.below !== null || p.above !== null) || result?.unconfigured_led_ids.length > 0 || result?.grips.some(p => ['below', 'above'].some(s => p[`${s}_status`] === 'ambiguous'));
    $('preview-grip').disabled = !reviewed || !selectedGrip;
    $('test-led').disabled = !reviewed || selectedLED === null;
    $('deactivate').disabled = !active;
    $('state').textContent = t(active ? 'active' : 'legacy');
    $('led-tab').setAttribute('aria-pressed', String(view === 'leds'));
    $('link-tab').setAttribute('aria-pressed', String(view === 'links'));
}
function changed() { reviewed = false; dirty = true; selectedLED = null; message(t('dirty')); buttons(); }
function parseIDs(text) {
    const ids = new Set();
    for (const token of text.trim().split(/[,;\s]+/).filter(Boolean)) {
        const match = token.match(/^(\d+)(?:[-–](\d+))?$/);
        if (!match) throw new Error(t('invalidnumbers'));
        const from = Number(match[1]), to = Number(match[2] ?? from);
        if (!Number.isSafeInteger(from) || !Number.isSafeInteger(to) || to < from || to - from > 10000) throw new Error(t('invalidnumbers'));
        for (let id = from; id <= to; id++) ids.add(id);
        if (ids.size > 10000) throw new Error(t('invalidnumbers'));
    }
    return [...ids].sort((a, b) => a - b);
}
function formToGrid() {
    const g = grid(); if (!g) return;
    g.name = $('name').value; g.surface = $('surface').value.trim();
    g.r = Number($('rows').value); g.c = Number($('columns').value);
    g.alternating = $('alternating').checked; g.alternating_start_column = $('offset').checked ? 1 : 0;
    g.led_start_corner = $('start').value; g.led_direction = $('path').value;
    g.physical_start = $('physical-start').value === '' ? null : Number($('physical-start').value);
}
function capture() {
    formToGrid(); layout.skipped_physical_ids = parseIDs($('skipped').value);
    layout.lateral_tolerance = Number($('tolerance').value); layout.max_distance = Number($('distance').value);
}
function insertionOptions(select, value = '') {
    select.replaceChildren(option(t('end'), ''));
    (result?.leds || []).filter(p => p.grid_id === grid()?.id && p.position_id >= 0).sort((a, b) => a.position_id - b.position_id).forEach(p =>
        select.appendChild(option(`${t('before')} ${p.position_id} · LED ${p.physical_id ?? '—'}`, p.position_id)));
    select.value = value;
}
function renderForm() {
    $('grid-select').replaceChildren(...layout.grids.map((g, i) => option(`${i + 1}. ${g.name}`, i)));
    $('grid-select').value = index;
    const g = grid(); $('grid-fields').hidden = !g;
    $('delete-grid').disabled = !g; $('earlier').disabled = index <= 0; $('later').disabled = index >= layout.grids.length - 1;
    if (!g) return;
    g.manual_positions ??= []; g.excluded_position_ids ??= [];
    for (const [id, value] of Object.entries({name:g.name, surface:g.surface, rows:g.r, columns:g.c, start:g.led_start_corner, path:g.led_direction, 'physical-start':g.physical_start ?? ''})) $(id).value = value;
    $('alternating').checked = !!g.alternating; $('offset').checked = g.alternating_start_column === 1;
    insertionOptions($('insert-before'));
    $('position-select').replaceChildren(...(result?.leds || []).filter(p => p.grid_id === g.id).map(p => option(`${p.position_id} · LED ${p.physical_id ?? '—'}`, p.position_id)));
    $('toggle-position').disabled = !reviewed;
    $('corner-inputs').replaceChildren();
    g.points.forEach((p, i) => {
        const label = document.createElement('label'); label.textContent = `${i + 1}: x / y`;
        ['x','y'].forEach(axis => { const input = document.createElement('input'); input.type = 'number'; input.step = '0.1'; input.min = 0; input.value = p[axis]; input.setAttribute('aria-label', `${i + 1} ${axis}`);
            input.addEventListener('change', () => { p[axis] = Number(input.value); changed(); draw(); }); label.appendChild(input); });
        $('corner-inputs').appendChild(label);
    });
    $('extra-list').replaceChildren();
    g.manual_positions.forEach(p => {
        const row = document.createElement('div'), label = document.createElement('span'), select = document.createElement('select'), remove = document.createElement('button');
        label.textContent = `${p.id}`; insertionOptions(select, p.before_position_id ?? '');
        row.appendChild(label);
        for (const axis of ['x','y']) {
            const input = document.createElement('input'); input.type = 'number'; input.min = '0'; input.value = p[axis];
            input.setAttribute('aria-label', `LED ${p.id} ${axis}`);
            input.addEventListener('change', () => { p[axis] = Number(input.value); changed(); });
            row.appendChild(input);
        }
        select.addEventListener('change', () => { p.before_position_id = select.value === '' ? null : Number(select.value); changed(); });
        remove.textContent = t('remove'); remove.addEventListener('click', () => { g.manual_positions = g.manual_positions.filter(other => other.id !== p.id); g.excluded_position_ids = g.excluded_position_ids.filter(id => id !== p.id); changed(); renderForm(); });
        row.append(select, remove); $('extra-list').appendChild(row);
    });
}
function svgElement(tag, attrs) { const e = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [key, value] of Object.entries(attrs)) e.setAttribute(key, value); return e; }
function draw() {
    const svg = $('overlay'); svg.replaceChildren();
    const w = initial.coordinate_width, h = initial.coordinate_height;
    svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
    const r = Math.max(3, w / 240), leds = new Map((result?.leds || []).filter(p => p.physical_id !== null).map(p => [p.physical_id, p]));
    const sx = w / layout.coordinate_width, sy = h / layout.coordinate_height;
    const grips = result?.grips || [];
    if (view === 'links') for (const p of grips) {
        if (selectedGrip && p.key !== selectedGrip) continue;
        for (const side of ['above','below']) { const led = leds.get(p[side]); if (!led) continue;
            svg.appendChild(svgElement('line', { x1:p.x, y1:p.y, x2:led.x, y2:led.y, stroke:side === 'above' ? '#1985f4' : '#f58b12', 'stroke-width':2 }));
        }
    }
    for (const p of grips) {
        const e = svgElement('circle', {cx:p.x, cy:p.y, r:r+1, fill:'#42e47b', stroke:p.key === selectedGrip ? '#fff' : '#18512c', 'stroke-width':p.key === selectedGrip ? 3 : 1});
        const title = svgElement('title', {}); title.textContent = gripLabel(p); e.appendChild(title);
        e.addEventListener('click', event => { if (pickMode) return; event.stopPropagation(); selectedGrip = p.key; setView('links'); }); svg.appendChild(e);
    }
    for (const p of result?.leds || []) {
        if (view === 'leds' && p.grid_id !== grid()?.id) continue;
        const e = svgElement('circle', {cx:p.x, cy:p.y, r, fill:p.physical_id === null ? '#666' : '#ffc044', stroke:p.physical_id === selectedLED ? '#fff' : '#553800', 'stroke-width':p.physical_id === selectedLED ? 3 : 1});
        const title = svgElement('title', {}); title.textContent = `LED ${p.physical_id ?? '—'} · ${p.grid_id} / ${p.position_id}`; e.appendChild(title);
        e.addEventListener('click', event => { if (pickMode) return; event.stopPropagation();
            selectedLED = p.physical_id;
            if (view === 'leds' && event.shiftKey) { const g = grid(); if (g.excluded_position_ids.includes(p.position_id)) g.excluded_position_ids = g.excluded_position_ids.filter(id => id !== p.position_id); else g.excluded_position_ids.push(p.position_id); changed(); }
            buttons(); draw();
        });
        svg.appendChild(e);
        const selected = grips.find(g => g.key === selectedGrip);
        if (view === 'leds' || (p.physical_id !== null && selected && [selected.below,selected.above].includes(p.physical_id))) { const text = svgElement('text', {x:p.x+r+2, y:p.y+4}); text.textContent = p.physical_id ?? '×'; svg.appendChild(text); }
    }
    if (view === 'leds') (pickMode === 'corners' ? picked : grid()?.points || []).forEach((p, i) => {
        svg.appendChild(svgElement('circle', {cx:p.x*sx, cy:p.y*sy, r:r+3, fill:'none', stroke:'#e54848', 'stroke-width':2}));
        const label = svgElement('text', {x:p.x*sx+10, y:p.y*sy-10}); label.textContent = i+1; svg.appendChild(label);
    });
}
function renderReview() {
    const grips = result?.grips || [];
    $('grip-select').replaceChildren(option(t('none'), ''), ...grips.map(p => option(gripLabel(p), p.key)));
    $('grip-select').value = selectedGrip || '';
    const selected = grips.find(p => p.key === selectedGrip);
    for (const side of ['below','above']) {
        const select = $(`${side}-override`); select.replaceChildren(option(t('automatic'), 'auto'), option(t('disabled'), 'none'));
        (result?.leds || []).filter(p => p.physical_id !== null && p.surface === selected?.surface).forEach(p => select.appendChild(option(`LED ${p.physical_id}`, p.physical_id)));
        const override = layout.overrides[selectedGrip];
        select.value = override && Object.hasOwn(override, side) ? (override[side] ?? 'none') : 'auto'; select.disabled = !selected;
    }
    $('summary').textContent = ['below','above'].map(side => `${t(side)}: ` + Object.entries(result?.summary[side] || {}).map(([status, count]) => `${t(status)} ${count}`).join(' · ')).join(' | ');
    $('associations').replaceChildren();
    for (const p of grips) {
        if ($('issues-only').checked && !['below','above'].some(s => ['missing','ambiguous'].includes(p[`${s}_status`]))) continue;
        const row = document.createElement('tr'); row.className = p.key === selectedGrip ? 'selected' : '';
        const first = document.createElement('td'), button = document.createElement('button'); button.textContent = gripLabel(p);
        button.addEventListener('click', () => { selectedGrip = p.key; renderReview(); draw(); buttons(); }); first.appendChild(button); row.appendChild(first);
        for (const side of ['below','above']) { const cell = document.createElement('td'); cell.textContent = `${p[side] ?? '—'} · ${t(p[`${side}_status`])}`; if (['missing','ambiguous'].includes(p[`${side}_status`])) cell.className = 'bad'; row.appendChild(cell); }
        $('associations').appendChild(row);
    }
}
function setView(next) { formToGrid(); view = next; $('grid-panel').hidden = view !== 'leds'; $('review-panel').hidden = view !== 'links'; renderReview(); draw(); buttons(); }
async function request(action = 'calculate') {
    try {
        if (action !== 'deactivate') capture();
        if (pickMode === 'corners') throw new Error(t('cornerhelp'));
        $('editor').inert = true;
        const response = await fetch(api, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({wallid:initial.wallid, action, layout:action === 'deactivate' ? null : layout})});
        const data = await response.json();
        if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data));
        active = data.active;
        if (action !== 'deactivate') { result = data; reviewed = true; }
        if (action === 'draft' || action === 'activate') dirty = false;
        renderForm(); renderReview(); draw(); buttons();
        message(action === 'activate' ? t('activated') : action === 'draft' ? t('saved') : action === 'deactivate' ? t('legacy') : (data.unconfigured_led_ids.length ? `${t('unconfigured')}: ${data.unconfigured_led_ids.join(', ')}` : $('summary').textContent));
        return true;
    } catch (error) { reviewed = false; buttons(); message(error.message, true); return false; }
    finally { $('editor').inert = false; }
}
async function preview(ids, enabled = true) {
    try {
        $('editor').inert = true;
        const response = await fetch(previewUrl, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({physical_led_ids:ids, enabled})});
        const data = await response.json();
        if (!response.ok || data.status === 'partial') throw new Error(data.detail || data.message || `HTTP ${response.status}`);
        previewActive = enabled; message(data.message);
    } catch (error) { message(error.message, true); }
    finally { $('editor').inert = false; }
}
function cancelPick() { pickMode = null; picked = []; $('cancel-pick').hidden = true; draw(); }
function newGrid(source) {
    formToGrid();
    const g = source ? clone(source) : {r:2,c:2,points:[],alternating:false,alternating_start_column:0,led_start_corner:'bottom_left',led_direction:'vertical',excluded_position_ids:[],manual_positions:[]};
    // A copied grip grid has logical numbering and calibration fields, not LED settings.
    const clean = {id:`led-${Date.now()}-${Math.random().toString(36).slice(2,8)}`, name:`LED ${layout.grids.length+1}`, surface:'1', physical_start:null};
    for (const key of ['r','c','points','alternating','alternating_start_column','led_start_corner','led_direction','excluded_position_ids','manual_positions']) clean[key] = g[key] ?? (key.endsWith('positions') || key === 'excluded_position_ids' ? [] : undefined);
    // Grip coordinates may be from a different image resolution than the draft.
    if (source) { const sx=layout.coordinate_width/initial.coordinate_width, sy=layout.coordinate_height/initial.coordinate_height; clean.points.forEach(p=>{p.x*=sx;p.y*=sy;}); clean.manual_positions.forEach(p=>{p.x*=sx;p.y*=sy;}); }
    layout.grids.push(clean); index = layout.grids.length-1; cancelPick(); changed(); renderForm(); draw();
}
$('grid-select').addEventListener('change', () => { formToGrid(); index=Number($('grid-select').value); cancelPick(); renderForm(); draw(); });
for (const id of ['name','surface','rows','columns','alternating','offset','start','path','physical-start']) $(id).addEventListener('change', () => { formToGrid(); changed(); });
for (const id of ['skipped','tolerance','distance']) $(id).addEventListener('input', changed);
$('add-grid').addEventListener('click', () => newGrid());
$('copy-grid').addEventListener('click', () => newGrid(gripGrids[Number($('copy-source').value)]));
$('delete-grid').addEventListener('click', () => { if (!window.confirm(t('deleteconfirm'))) return; layout.grids.splice(index,1); index=Math.max(0,index-1); cancelPick(); changed(); renderForm(); draw(); });
for (const [id, delta] of [['earlier',-1],['later',1]]) $(id).addEventListener('click', () => { formToGrid(); const target=index+delta; [layout.grids[index],layout.grids[target]]=[layout.grids[target],layout.grids[index]]; index=target; changed(); renderForm(); });
$('pick-corners').addEventListener('click', () => { pickMode='corners'; picked=[]; $('cancel-pick').hidden=false; message(t('cornerhelp')); draw(); });
$('cancel-pick').addEventListener('click', cancelPick);
$('add-point').addEventListener('click', () => { pickMode='extra'; $('cancel-pick').hidden=false; message(t('addpoint')); });
$('shift-grid').addEventListener('click', () => { formToGrid(); const g=grid(), step=Number($('shift').value)/Math.max(1,g.r-1); if (g.points.length!==4 || !Number.isFinite(step)) return;
    const p=clone(g.points); for (const [top,bottom] of [[0,3],[1,2]]) for (const k of [top,bottom]) { g.points[k].x+= (p[bottom].x-p[top].x)*step; g.points[k].y+=(p[bottom].y-p[top].y)*step; }
    changed(); renderForm(); draw(); });
$('overlay').addEventListener('click', event => {
    if (!pickMode || !grid()) return;
    const rect=$('overlay').getBoundingClientRect(), p={x:Math.round((event.clientX-rect.left)/rect.width*layout.coordinate_width),y:Math.round((event.clientY-rect.top)/rect.height*layout.coordinate_height)};
    if (pickMode==='corners') { picked.push(p); if (picked.length===4) { grid().points=clone(picked); cancelPick(); changed(); renderForm(); } }
    else { const g=grid(); g.manual_positions.push({id:Math.min(0,...g.manual_positions.map(p=>p.id))-1,...p,before_position_id:$('insert-before').value===''?null:Number($('insert-before').value)}); changed(); renderForm(); }
    draw();
});
$('led-tab').addEventListener('click', () => setView('leds'));
$('link-tab').addEventListener('click', () => setView('links'));
for (const [id, action] of [['calculate','calculate'],['save-draft','draft'],['activate','activate'],['deactivate','deactivate']]) $(id).addEventListener('click', () => request(action));
$('grip-select').addEventListener('change', () => { selectedGrip=$('grip-select').value || null; renderReview(); draw(); buttons(); });
$('issues-only').addEventListener('change', renderReview);
for (const side of ['below','above']) $(`${side}-override`).addEventListener('change', () => { if (!selectedGrip) return; const value=$(`${side}-override`).value; const o=layout.overrides[selectedGrip] ??= {}; if (value==='auto') delete o[side]; else o[side]=value==='none'?null:Number(value); if (!Object.keys(o).length) delete layout.overrides[selectedGrip]; changed(); });
$('preview-grip').addEventListener('click', () => { if (!reviewed) return; const p=result.grips.find(p=>p.key===selectedGrip); const sides=$('test-side').value==='both'?['below','above']:[$('test-side').value]; const ids=[...new Set(sides.map(s=>p?.[s]).filter(id=>id!==null && id!==undefined))]; if (ids.length) preview(ids); else message(t('missing')); });
$('test-led').addEventListener('click', () => { if (reviewed && selectedLED!==null) preview([selectedLED]); });
$('position-select').addEventListener('change', () => { const p=result?.leds.find(p=>p.grid_id===grid()?.id && p.position_id===Number($('position-select').value)); selectedLED=p?.physical_id ?? null; buttons(); draw(); });
$('toggle-position').addEventListener('click', () => { if (!reviewed || !grid()) return; const id=Number($('position-select').value), g=grid(); if (g.excluded_position_ids.includes(id)) g.excluded_position_ids=g.excluded_position_ids.filter(p=>p!==id); else g.excluded_position_ids.push(id); changed(); $('toggle-position').disabled=true; });
$('stop-preview').addEventListener('click', () => preview([],false));
window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue=''; } });
window.addEventListener('pagehide', () => { if (previewActive) navigator.sendBeacon(previewUrl,new Blob([JSON.stringify({physical_led_ids:[],enabled:false})],{type:'application/json'})); });
window.addEventListener('crux-language-change', () => { renderForm(); renderReview(); buttons(); if ($('status').className !== 'error') message(reviewed ? $('summary').textContent : t('dirty')); });
$('copy-source').replaceChildren(...gripGrids.map((g,i)=>option(`${t('grid')} ${i+1}`,i)));
gripGrids.forEach((g,i)=>{ const label=document.createElement('label'), input=document.createElement('input'), id=gridId(g,i); label.textContent=`${t('grid')} ${i+1}`; input.value=layout.grip_surfaces[id] || '1'; input.maxLength=100; input.addEventListener('change',()=>{layout.grip_surfaces[id]=input.value.trim();changed();}); label.appendChild(input); $('grip-surfaces').appendChild(label); });
$('skipped').value=layout.skipped_physical_ids.join(', '); $('tolerance').value=layout.lateral_tolerance; $('distance').value=layout.max_distance;
renderForm(); buttons(); draw(); void request('calculate');
