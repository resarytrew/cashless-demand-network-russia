'use strict';

// Category changes follow scroll position only. There is no autoplay clock.
window.createAtlasScrollChapter = function ({id, stage, mount, count, getIndex, select, ready = () => true}) {
  if (!window.gsap || !window.ScrollTrigger) return {pause(){},refresh(){}};
  const controls = document.createElement('div');
  controls.className = 'auto-tour scroll-chapter';
  controls.dataset.tour = id;
  controls.innerHTML = '<span class="tour-mode">Листайте прокруткой</span><span class="tour-position"></span><span class="tour-track" aria-hidden="true"><i></i></span>';
  mount.append(controls);
  const media = gsap.matchMedia();
  let stopped = false, lastStep = -1, trigger, manualScroll;
  function sync() {
    controls.querySelector('.tour-position').textContent = `${getIndex()+1} / ${count}`;
    controls.querySelector('.tour-track i').style.transform = `scaleX(${(getIndex()+1)/count})`;
  }
  const api = {
    // Keep a direct selection until scroll crosses a new chapter threshold.
    pause(){
      if(trigger){
        lastStep=Math.min(count-1,Math.floor(trigger.progress*count));
        manualScroll=trigger.scroll();
      }
      sync();
    }, refresh:sync,
    destroy(){stopped=true;media.revert();}
  };
  media.add({all:'all',motion:'(prefers-reduced-motion: no-preference)',desktop:'(min-width: 1000px)'}, context => {
    controls.dataset.state = context.conditions.motion ? 'scroll' : 'manual';
    controls.querySelector('.tour-mode').textContent = context.conditions.motion ? 'Листайте прокруткой' : 'Выберите вкладку';
    if (!context.conditions.motion) return;
    stage.classList.add('scroll-stage');
    // Never trap a panel taller than the screen: small screens retain native scrolling.
    const fits = context.conditions.desktop && stage.offsetHeight < innerHeight - 44;
    lastStep = -1;
    trigger = ScrollTrigger.create({
      id:`chapter-${id}`,trigger:stage,
      start:fits ? 'top 22px' : 'top 65%',
      end:fits ? ()=>'+='+Math.round(innerHeight*.48*(count-1)) : 'bottom 30%',
      pin:fits ? stage : false,pinSpacing:true,anticipatePin:1,invalidateOnRefresh:true,
      onUpdate:self=>{
        if(stopped || !ready() || !self.isActive) return;
        // Layout/focus updates after a click can fire ScrollTrigger without a
        // user scroll. Preserve the direct selection until scroll really moves.
        if(manualScroll!==undefined){
          if(Math.abs(self.scroll()-manualScroll)<12){sync();return;}
          manualScroll=undefined;
        }
        const step=Math.min(count-1,Math.floor(self.progress*count));
        if(step===lastStep)return;
        lastStep=step;
        if(getIndex()!==step) select(step);
        sync();
      }
    });
    controls.dataset.pinned=String(fits);
    return ()=>{trigger.kill();trigger=null;stage.classList.remove('scroll-stage');};
  });
  window.addEventListener('beforeprint',api.destroy,{once:true});
  sync();
  return api;
};
