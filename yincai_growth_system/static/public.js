document.addEventListener("DOMContentLoaded",function(){
  const toggle=document.querySelector(".menu-toggle"),nav=document.querySelector(".main-nav");
  if(toggle&&nav){toggle.addEventListener("click",function(){const open=nav.classList.toggle("open");toggle.setAttribute("aria-expanded",String(open));document.body.classList.toggle("menu-open",open)});nav.querySelectorAll("a").forEach(a=>a.addEventListener("click",()=>{nav.classList.remove("open");document.body.classList.remove("menu-open")}))}
  document.querySelectorAll("form[data-working]").forEach(form=>form.addEventListener("submit",function(){if(!form.checkValidity())return;const button=form.querySelector("button[type=submit],button:not([type])");if(button&&!button.disabled){button.dataset.label=button.textContent;button.textContent=form.dataset.working;button.classList.add("working")}}));
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting)entry.target.classList.add("visible")}),{threshold:.12});
  document.querySelectorAll(".solution-grid article,.process-grid article,.product-card,.video-frame").forEach(el=>observer.observe(el));
});
