<?php
/* CMLC · Buscador del blog (solo en /category/radiologia-e-imagen/)
   Filtra client-side las .blog-card que el tema ya renderiza. Se inserta vía
   wp_footer (fuera de the_content, no sufre wptexturize) y se reubica con JS
   justo antes de .blog-grid. Snippet PHP en WPCode. */
add_action('wp_footer', function () {
    if (!is_category('radiologia-e-imagen')) return;
?>
<div id="cmlc-search" style="display:none">
  <style>
  #cmlc-search{--cs-navy:#0C2C5A;--cs-blue:#1968AE;--cs-cyan:#34B3E4;--cs-ink:#0A1E3A;
    --cs-slate:#54637A;--cs-line:#E4ECF5;--cs-paper:#F4F8FC;--cs-white:#fff;--cs-radius:18px;
    max-width:1160px;margin:0 auto;padding:0 24px 8px;font-family:inherit}
  #cmlc-search *{box-sizing:border-box}
  #cmlc-bar{display:flex;align-items:center;gap:11px;background:var(--cs-white);
    border:1.5px solid var(--cs-line);border-radius:14px;padding:0 16px;max-width:560px;
    box-shadow:0 1px 2px rgba(10,30,58,.05);transition:border-color .2s,box-shadow .2s}
  #cmlc-bar:focus-within{border-color:var(--cs-blue);box-shadow:0 0 0 4px rgba(25,104,174,.14)}
  #cmlc-bar svg{flex:none;width:19px;height:19px;color:var(--cs-slate)}
  #cmlc-bar:focus-within svg{color:var(--cs-blue)}
  #cmlc-input{flex:1;border:0!important;background:none!important;outline:none;color:var(--cs-ink)!important;
    font-family:inherit;font-size:1rem;padding:13px 0}
  #cmlc-input::placeholder{color:var(--cs-slate)}
  #cmlc-input::-webkit-search-cancel-button{display:none}
  #cmlc-clear{flex:none;border:0!important;background:var(--cs-paper)!important;color:var(--cs-slate)!important;
    width:24px!important;height:24px!important;min-height:0!important;border-radius:50%!important;
    cursor:pointer;font-size:1rem!important;line-height:1!important;padding:0!important;margin:0!important;
    display:grid!important;place-items:center!important;box-shadow:none!important;transition:background .15s,color .15s}
  #cmlc-clear:hover{background:var(--cs-blue)!important;color:#fff!important}
  #cmlc-hint{color:var(--cs-slate);font-size:.85rem;margin:10px 0 0}
  #cmlc-hint kbd{font-family:ui-monospace,Consolas,monospace;background:var(--cs-paper);
    border:1px solid var(--cs-line);border-radius:5px;padding:1px 6px;font-size:.78rem;color:var(--cs-ink)}
  #cmlc-count{font-size:.8rem;font-weight:600;letter-spacing:.03em;text-transform:uppercase;
    color:var(--cs-slate);margin:18px 0 0}
  #cmlc-count b{color:var(--cs-ink)}
  .blog-card.cmlc-hidden{display:none!important}
  #cmlc-empty{max-width:1160px;margin:18px auto 0;padding:0 24px;color:var(--cs-slate);display:none}
  #cmlc-empty .cmlc-reset{background:none;border:0;color:var(--cs-blue);font-weight:600;cursor:pointer;
    text-decoration:underline;font:inherit;padding:0;margin-left:4px}
  </style>
  <div id="cmlc-bar">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"></circle><path d="m20 20-3.2-3.2"></path></svg>
    <input id="cmlc-input" type="search" autocomplete="off" spellcheck="false" placeholder="Busca un tema: tomografía, ultrasonido, mastografía…" aria-label="Buscar en el blog">
    <button id="cmlc-clear" type="button" hidden aria-label="Limpiar búsqueda">&times;</button>
  </div>
  <p id="cmlc-hint">Filtra al instante mientras escribes · atajo <kbd>/</kbd></p>
  <p id="cmlc-count"></p>
</div>
<div id="cmlc-empty">
  No encontramos artículos sobre tu búsqueda.
  <button type="button" class="cmlc-reset">Ver todos</button>
</div>
<script>
(function(){
  function init(){
    var grid = document.querySelector('.blog-grid');
    var search = document.getElementById('cmlc-search');
    var emptyBox = document.getElementById('cmlc-empty');
    if(!grid || !search) return;
    grid.parentNode.insertBefore(search, grid);
    grid.parentNode.insertBefore(emptyBox, grid.nextSibling);
    search.style.display = '';

    var input=document.getElementById('cmlc-input'), clearBtn=document.getElementById('cmlc-clear'),
        countEl=document.getElementById('cmlc-count'), resetBtn=emptyBox.querySelector('.cmlc-reset');
    var cards=Array.prototype.slice.call(grid.querySelectorAll('.blog-card'));
    var TOTAL=cards.length;
    if(!TOTAL) return;

    // Sinónimos de estudios/temas de radiología (edita libremente; minúsculas sin acentos).
    var SYN=[
      ['rayos x','radiografia','rx'],
      ['tomografia','tac','tomografia multicorte'],
      ['ultrasonido','ecografia','doppler'],
      ['mastografia','mamografia'],
      ['densitometria','densitometria osea'],
      ['panoramica dental','ortopantomografia'],
      ['electrocardiograma','ekg','ecg'],
      ['a domicilio','en casa','a domicilio'],
      ['preparacion','ayuno','indicaciones'],
      ['contraste','estudio contrastado'],
      ['radiacion','dosis de radiacion']
    ];
    function expandSyn(base){
      var add=[];
      for(var i=0;i<SYN.length;i++){var g=SYN[i];
        for(var j=0;j<g.length;j++){ if(base.indexOf(g[j])>=0){add=add.concat(g);break;} }
      }
      return add.length?base+' '+add.join(' '):base;
    }
    function foldChar(c){var n=c.normalize('NFD');return (n[0]||c).toLowerCase();}
    function fold(s){return Array.from(s).map(foldChar).join('');}

    cards.forEach(function(c){
      var title=(c.querySelector('h2')||{}).textContent||'';
      var ex=(c.querySelector('p')||{}).textContent||'';
      c._h=expandSyn(fold(title+' '+ex));
    });

    function apply(){
      var raw=input.value.trim(), terms=fold(raw).split(/\s+/).filter(Boolean);
      var shown=0;
      cards.forEach(function(c){
        var match=!terms.length||terms.every(function(t){ return c._h.indexOf(t)>=0; });
        c.classList.toggle('cmlc-hidden', !match);
        if(match) shown++;
      });
      clearBtn.hidden=!raw;
      if(shown===0){
        emptyBox.style.display='';
        countEl.innerHTML='<b>0</b> resultados';
      }else{
        emptyBox.style.display='none';
        countEl.innerHTML=raw?'<b>'+shown+'</b> de '+TOTAL+' artículos':'Mostrando los <b>'+TOTAL+'</b> artículos';
      }
    }
    input.addEventListener('input',apply);
    clearBtn.addEventListener('click',function(){input.value='';apply();input.focus();});
    if(resetBtn) resetBtn.addEventListener('click',function(){input.value='';apply();input.focus();});
    document.addEventListener('keydown',function(e){
      if(e.key==='/'&&document.activeElement!==input){e.preventDefault();input.focus();}
      else if(e.key==='Escape'&&document.activeElement===input&&input.value){input.value='';apply();}
    });
    apply();
  }
  if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded', init); }
  else { init(); }
})();
</script>
<?php
});
