// Shared image navigation. Geometry always stays in original image coordinates.
function installImageZoom(viewport, content, {canPan = () => true, onChange = () => {}} = {}) {
    let scale = 1, fit = 1, gesture = null, suppressClick = false;
    const pointers = new Map();
    function setScale(next, x, y) {
        const rect = viewport.getBoundingClientRect();
        x ??= rect.left + rect.width / 2; y ??= rect.top + Math.min(rect.height, viewport.clientHeight || rect.height) / 2;
        const px = x - rect.left, py = y - rect.top;
        const rx = ((viewport.scrollLeft || 0) + px) / scale, ry = ((viewport.scrollTop || 0) + py) / scale;
        scale = Math.max(1, Math.min(8, next)); content.style.width = `${fit * scale * 100}%`;
        viewport.scrollLeft = rx * scale - px; viewport.scrollTop = ry * scale - py;
        onChange(scale);
    }
    viewport.addEventListener('wheel', event => {
        if (event.target === viewport) return; // Empty margin remains page-scrollable.
        event.preventDefault(); setScale(scale * Math.exp(-event.deltaY * .002), event.clientX, event.clientY);
    }, {passive:false});
    viewport.addEventListener('pointerdown', event => {
        if (!pointers.size) suppressClick = false;
        pointers.set(event.pointerId, {x:event.clientX,y:event.clientY});
        if (pointers.size === 2) {
            const [a,b] = [...pointers.values()]; gesture = {type:'pinch',distance:Math.hypot(a.x-b.x,a.y-b.y),scale};
            suppressClick = true;
        } else if (canPan() && (scale > 1 || event.button === 1)) {
            gesture = {type:'pan',x:event.clientX,y:event.clientY,left:viewport.scrollLeft || 0,top:viewport.scrollTop || 0};
        }
    }, true);
    viewport.addEventListener('pointermove', event => {
        if (!pointers.has(event.pointerId)) return;
        pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
        if (gesture?.type === 'pinch' && pointers.size >= 2) {
            const [a,b] = [...pointers.values()];
            setScale(gesture.scale * Math.hypot(a.x-b.x,a.y-b.y) / Math.max(1,gesture.distance), (a.x+b.x)/2, (a.y+b.y)/2);
            event.preventDefault();
        } else if (gesture?.type === 'pan') {
            const dx=event.clientX-gesture.x, dy=event.clientY-gesture.y;
            if (Math.hypot(dx,dy)>4) { suppressClick=true; viewport.setPointerCapture?.(event.pointerId); }
            viewport.scrollLeft=gesture.left-dx; viewport.scrollTop=gesture.top-dy;
        }
    }, true);
    const end = event => { pointers.delete(event.pointerId); gesture=null; };
    viewport.addEventListener('pointerup',end,true); viewport.addEventListener('pointercancel',end,true);
    window.addEventListener('pointerup',end,true); window.addEventListener('pointercancel',end,true);
    viewport.addEventListener('click',event=>{ if(suppressClick){suppressClick=false;event.preventDefault();event.stopImmediatePropagation();} },true);
    return {setScale, zoom:factor=>setScale(scale*factor), reset:()=>{
        content.style.width='100%';
        const height=content.getBoundingClientRect().height;
        fit=height>0&&viewport.clientHeight>0?Math.min(1,viewport.clientHeight/height):1;
        setScale(1);viewport.scrollLeft=0;viewport.scrollTop=0;
    },
        isPinching:()=>pointers.size>1, isPanning:()=>gesture?.type==='pan', scale:()=>scale};
}
