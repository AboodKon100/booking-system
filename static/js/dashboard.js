/* Shared Noomly dashboard JS */
function toggleSidebar(){
  var s=document.getElementById('sidebar');
  var o=document.getElementById('sidebar-overlay');
  if(s) s.classList.toggle('open');
  if(o) o.classList.toggle('open');
}
function initTheme(){
  var t=localStorage.getItem('theme');
  if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme:dark)').matches)){
    document.documentElement.classList.add('dark');
  }else{
    document.documentElement.classList.remove('dark');
  }
}
function toggleTheme(){
  document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme',document.documentElement.classList.contains('dark')?'dark':'light');
}
initTheme();
