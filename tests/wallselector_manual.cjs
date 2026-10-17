// Exercise the actual generated page script with a minimal DOM, without WLED.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(0, 'utf8');
const scripts = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)];
const nodes = [];
class Element {
    constructor(tag = 'div') {
        this.tagName = tag; this.children = []; this.listeners = {};
        this.style = {}; this.dataset = {}; this.className = '';
        this._value = ''; this.checked = false; this.disabled = false;
        this.classList = { add() {}, remove() {} };
        nodes.push(this);
    }
    get value() { return this._value; }
    set value(value) { this._value = String(value); }
    get selectedIndex() { return this.children.findIndex(o => o.value === this.value); }
    appendChild(child) { child.parent = this; this.children.push(child); }
    append(...children) { children.forEach(c => this.appendChild(c)); }
    replaceChildren(...children) { this.children = []; this.append(...children); }
    add(option) { this.appendChild(option); }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(c => c !== this); this.removed = true; }
    setAttribute(name, value) { (this.attributes ??= {})[name] = String(value); }
    getAttribute(name) { return this.attributes?.[name]; }
    addEventListener(type, handler) { (this.listeners[type] ??= []).push(handler); }
    fire(type, props = {}) { return Promise.all((this.listeners[type] || []).map(h => h({ preventDefault() {}, stopPropagation() {}, ...props }))); }
    getBoundingClientRect() { return { left: 0, top: 0, width: 200, height: 100 }; }
}
const ids = new Map();
for (const id of [...html.matchAll(/id="([^"]+)"/g)].map(m => m[1])) ids.set(id, new Element());
ids.get('climbing-image').complete = true;
ids.get('climbing-image').naturalWidth = 200;
ids.get('climbing-image').naturalHeight = 100;
const document = {
    body: new Element('body'),
    getElementById: id => ids.get(id),
    createElement: tag => new Element(tag),
    querySelectorAll: selector => nodes.filter(n => !n.removed && n.className.split(' ').includes(selector.slice(1))),
};
const alerts = [];
const context = vm.createContext({
    document, console, alert: message => alerts.push(message),
    window: { cruxI18n: { t: (key, replacements = {}) => key + JSON.stringify(replacements) }, confirm: () => true, addEventListener() {} },
    Option: function(text, value) { const o = new Element('option'); o.textContent = text; o.value = value; return o; },
});
vm.runInContext(scripts.at(-1)[1], context);
const run = code => vm.runInContext(code, context);
const read = code => JSON.parse(run(`JSON.stringify(${code})`));
const order = () => read('grids[0].position_order');
const click = (x, y) => ids.get('image-container').fire('click', { clientX: x, clientY: y });

(async () => {
    assert.equal(ids.get('add-hole-mode').disabled, false);
    assert.match(ids.get('manual-status').textContent, /manual.ready/);
    assert.deepEqual(order(), [0, 1, 2]);
    await ids.get('add-hole-mode').fire('click');
    assert.equal(ids.get('add-hole-mode').getAttribute('aria-pressed'), 'true');
    assert.match(ids.get('manual-status').textContent, /manual.active/);
    assert.match(ids.get('add-hole-mode').textContent, /manual.done/);
    run("manualInsertBefore.value = '1'");
    // Image is displayed at twice the saved coordinate dimensions.
    await click(50, 40);
    assert.deepEqual(read('grids[0].manual_positions'), [{ id: -1, x: 25, y: 20, before_position_id: 1 }]);
    assert.deepEqual(order(), [0, -1, 1, 2]);
    assert.deepEqual(read('grids[0].position_hold_ids'), { 1: 'hold-b' });
    assert.equal(read('grids[1].led_start'), 4);
    await click(50, 40); // Duplicate coordinates are ignored.
    assert.equal(read('grids[0].manual_positions.length'), 1);
    await click(70, 40);
    assert.deepEqual(order(), [0, -1, -2, 1, 2]);

    // Normal marker clicks toggle only exclusions, never positional identity.
    await ids.get('add-hole-mode').fire('click');
    assert.equal(ids.get('add-hole-mode').getAttribute('aria-pressed'), 'false');
    let marker = document.querySelectorAll('.grid-point').find(n => n.dataset.positionId === '-1');
    await marker.fire('click');
    assert.deepEqual(read('grids[0].excluded_position_ids'), [-1]);
    assert.equal(read('grids[0].position_led_ids[1]'), 2);
    marker = document.querySelectorAll('.grid-point').find(n => n.dataset.positionId === '-1');
    await marker.fire('click');
    assert.deepEqual(read('grids[0].excluded_position_ids'), []);

    // Change an extra hole's insertion point using the real list control.
    let select = ids.get('manual-list').children[0].children[1];
    select.value = '';
    await select.fire('change');
    assert.deepEqual(order(), [0, -2, 1, 2, -1]);
    run('loadGrid(1); loadGrid(0)');
    assert.deepEqual(order(), [0, -2, 1, 2, -1]);
    assert.equal(ids.get('add-hole-mode').getAttribute('aria-pressed'), 'false');

    // Remove first extra hole, preserving the other stable ID and labels.
    await ids.get('manual-list').children[0].children[2].fire('click');
    assert.deepEqual(order(), [0, -2, 1, 2]);
    assert.deepEqual(read('grids[0].position_hold_ids'), { 1: 'hold-b' });

    // Capture the real outbound request (no network or persistent writes).
    let sent;
    context.fetch = async (_url, options) => {
        sent = JSON.parse(options.body);
        assert.equal(document.body.inert, true);
        return { ok: false, status: 503, json: async () => ({ detail: 'simulated failure' }) };
    };
    await ids.get('submit-btn').fire('click');
    assert.deepEqual(sent.grids[0].manual_positions, [{ id: -2, x: 35, y: 20, before_position_id: 1 }]);
    assert.equal(document.body.inert, false);
    assert.deepEqual(order(), [0, -2, 1, 2]); // Failed save retains edits.

    // A successful save/reload keeps the extra hole and the visible entry point.
    const persistedGrids = read('grids');
    context.fetch = async () => ({ ok: true, json: async () => ({ grids: persistedGrids, holds2led: { 'hold-b': 2 } }) });
    await ids.get('submit-btn').fire('click');
    assert.equal(ids.get('add-hole-mode').disabled, false);
    assert.deepEqual(read('grids[0].manual_positions'), [{ id: -2, x: 35, y: 20, before_position_id: 1 }]);
    await ids.get('add-hole-mode').fire('click');
    await ids.get('image-container').fire('contextmenu');
    assert.equal(ids.get('add-hole-mode').getAttribute('aria-pressed'), 'false');
    assert.match(ids.get('manual-status').textContent, /manual.ready/);

    // Geometry changes require saving first; scaling updates both sources.
    ids.get('rows').value = 2;
    await ids.get('rows').fire('change');
    assert.equal(ids.get('add-hole-mode').disabled, true);
    assert.match(ids.get('manual-status').textContent, /manual.pending/);
    run('savedCreation.coordinate_width = 50; savedCreation.coordinate_height = 25; normalizeSavedCreationCoordinates()');
    assert.deepEqual(read('grids[0].manual_positions[0]'), { id: -2, x: 70, y: 40, before_position_id: 1 });
    assert.deepEqual(read('grids[0].positions[-2]'), [70, 40]);
    await ids.get('reset-btn').fire('click');
    assert.deepEqual(read('grids[0].manual_positions'), []);
    assert.equal(ids.get('add-hole-mode').disabled, true);
    assert.match(ids.get('manual-status').textContent, /manual.setup/);
    await ids.get('add-hole-mode').fire('click');
    assert.equal(ids.get('add-hole-mode').getAttribute('aria-pressed'), 'false');
    console.log('Manual-hole UI behavior passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
