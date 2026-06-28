const API = window.location.origin;

/* ---------- helpers ---------- */
function esc(s){return (s==null?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function confBand(s){if(s==null)return'na';if(s>=0.75)return'high';if(s>=0.5)return'mid';return'low'}
function meter(score){
  const pct = score==null?0:Math.round(score*100);
  return `<div class="meter meter--${confBand(score)}"><div class="meter-track"><div class="meter-fill" style="width:${pct}%"></div></div><span class="meter-val">${score==null?'—':Number(score).toFixed(2)}</span></div>`;
}
function stamp(status){
  const m={approved:['Təsdiq','is-verified'],pending_review:['Yoxlama','is-review'],rejected:['Rədd','is-rejected']};
  const [l,c]=m[status]||['Təsdiq','is-verified'];
  return `<span class="stamp ${c}">${l}</span>`;
}

/* ---------- sources ---------- */
async function fetchUniversities(){
  try{
    const data = await (await fetch(`${API}/universities`)).json();
    const el = document.getElementById('uniList'); el.innerHTML='';
    if(!data.length){el.innerHTML='<p class="muted">Hələ mənbə yoxdur — yuxarıdan əlavə edin və ya demo datanı yükləyin.</p>';return}
    data.forEach(u=>{
      el.innerHTML += `
      <div class="source">
        <div class="source-info">
          <div class="source-name">${esc(u.name)}</div>
          <div class="source-url">${esc(u.website_url)}</div>
        </div>
        <div class="source-actions">
          <button class="iconbtn run" title="Pipeline işə sal" onclick="runPipeline(${u.id})">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
          </button>
          <button class="iconbtn sim" title="Növbəti skrapı təqlid et (dəyişiklik aşkarlama)" onclick="simulateUpdate(${u.id})">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-2.6-6.4M21 3v6h-6"/></svg>
          </button>
        </div>
      </div>`;
    });
  }catch(e){console.error(e)}
}

async function addUniversity(){
  const name=document.getElementById('uniName').value.trim();
  const url=document.getElementById('uniUrl').value.trim();
  if(!name||!url)return alert('Ad və URL xanalarını doldurun.');
  try{
    const res=await fetch(`${API}/universities`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,website_url:url})});
    if(res.ok){document.getElementById('uniName').value='';document.getElementById('uniUrl').value='';fetchUniversities()}
  }catch(e){alert('Əlavə etmə uğursuz oldu.')}
}

async function seedDatabase(){
  try{
    const d=await (await fetch(`${API}/seed`,{method:'POST'})).json();
    alert(`Demo data yükləndi — ${d.universities_added} universitet, ${d.programs_added} proqram.`);
    fetchUniversities();
  }catch(e){alert('Seed uğursuz oldu.')}
}

async function resetDatabase(){
  if(!confirm('Bütün məlumat (universitetlər, proqramlar, jurnal) tam silinəcək. Davam edilsin?'))return;
  try{
    await fetch(`${API}/reset`,{method:'POST'});
    document.getElementById('resultsArea').classList.add('hidden');
    document.getElementById('emptyArea').classList.remove('hidden');
    fetchUniversities();
  }catch(e){alert('Sıfırlama uğursuz oldu.')}
}

/* ---------- pipeline run ---------- */
async function runPipeline(id){
  const ov=document.getElementById('loadingOverlay');
  ov.classList.remove('hidden'); animatePipeline();
  try{
    const data=await (await fetch(`${API}/universities/${id}/run-agent-pipeline`,{method:'POST'})).json();
    if(data.status==='success'){
      const m=data.metrics;
      document.getElementById('mProcessed').innerText=m.total_processed;
      document.getElementById('mNew').innerText=m.new_added;
      document.getElementById('mUpdated').innerText=m.updated_fees;
      document.getElementById('mUnchanged').innerText=m.unchanged;
      document.getElementById('mPending').innerText=m.pending_count ?? 0;
      document.getElementById('mConf').innerText=(m.avg_confidence!=null?Number(m.avg_confidence).toFixed(2):'—');
      document.getElementById('uniBadge').innerText=data.university_name;
      document.getElementById('reportText').innerText=data.reviewer_report;
      const a=document.getElementById('usedUrl'); a.href=data.source_url_used; a.innerText=data.source_url_used;
      showResults(id);
    }else{alert(data.message||'Pipeline tamamlanmadı.')}
  }catch(e){alert('Daxili xəta.')}
  finally{ov.classList.add('hidden')}
}

function showResults(id){
  document.getElementById('emptyArea').classList.add('hidden');
  document.getElementById('resultsArea').classList.remove('hidden');
  fetchPrograms(id); fetchChanges(id); fetchPendingPrograms();
}
function runPipelineRefresh(id){showResults(id)}

/* ---------- records ---------- */
async function fetchPrograms(uniId){
  try{
    const data=await (await fetch(`${API}/universities/${uniId}/programs`)).json();
    const b=document.getElementById('programsBody'); b.innerHTML='';
    if(!data.length){b.innerHTML='<tr><td colspan="7" class="muted" style="padding:16px">Proqram tapılmadı.</td></tr>';return}
    data.forEach(p=>{
      b.innerHTML += `
      <tr>
        <td><div class="pname">${esc(p.program_name)||'—'}</div><div class="sub" style="font-size:11.5px">${esc(p.faculty)||''}</div></td>
        <td class="cell-mono">${esc(p.degree)||'—'}</td>
        <td>${esc(p.language)||'—'}</td>
        <td class="cell-mono">${esc(p.tuition_fee)||'—'}</td>
        <td class="cell-mono">${esc(p.application_deadline)||'—'}</td>
        <td>${meter(p.confidence_score)}</td>
        <td>${stamp(p.status)}</td>
      </tr>`;
    });
  }catch(e){console.error(e)}
}

/* ---------- change ledger ---------- */
async function fetchChanges(uniId){
  try{
    const data=await (await fetch(`${API}/universities/${uniId}/changes`)).json();
    const c=document.getElementById('changesContainer'); c.innerHTML='';
    if(!data.length){c.innerHTML='<p class="muted">Hələ dəyişiklik yoxdur. Eyni mənbəni təkrar işə salanda fərqlər burada görünəcək.</p>';return}
    data.forEach(ch=>{
      c.innerHTML += `
      <div class="change">
        <div class="change-top">
          <span class="change-prog">${esc(ch.program_name)||'Proqram'}</span>
          <span class="field-tag">${esc(ch.field_name)}</span>
        </div>
        <div class="diff"><span class="old">${esc(ch.old_value)||'∅'}</span><span class="arrow">→</span><span class="new">${esc(ch.new_value)||'∅'}</span></div>
      </div>`;
    });
  }catch(e){console.error(e)}
}

/* ---------- verification queue ---------- */
async function fetchPendingPrograms(){
  try{
    const data=await (await fetch(`${API}/programs/pending`)).json();
    const c=document.getElementById('pendingContainer'); c.innerHTML='';
    if(!data.length){c.innerHTML='<p class="muted">Təsdiq gözləyən şübhəli qeyd yoxdur.</p>';return}
    data.forEach(p=>{
      c.innerHTML += `
      <div class="qitem flag">
        <div class="qinfo">
          <div class="qhead">${stamp('pending_review')}<span class="qname"><b>${esc(p.university_name)}</b> · ${esc(p.program_name)}</span></div>
          <div class="qmeta">${esc(p.faculty)||'Fakültə yoxdur'} · ${esc(p.tuition_fee)||'—'} · ${esc(p.language)||'—'} · son tarix ${esc(p.application_deadline)||'—'} · bal ${p.confidence_score!=null?Number(p.confidence_score).toFixed(2):'—'}</div>
        </div>
        <div class="qactions">
          <button class="act ok" onclick="approveProgram(${p.id})"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6 9 17l-5-5"/></svg>Təsdiqlə</button>
          <button class="act no" onclick="rejectProgram(${p.id})"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>Rədd et</button>
        </div>
      </div>`;
    });
  }catch(e){console.error(e)}
}

async function approveProgram(id){try{if((await fetch(`${API}/programs/${id}/approve`,{method:'POST'})).ok)fetchPendingPrograms()}catch(e){alert('Təsdiqləmə uğursuz oldu.')}}
async function rejectProgram(id){try{if((await fetch(`${API}/programs/${id}/reject`,{method:'POST'})).ok)fetchPendingPrograms()}catch(e){alert('Rədd etmə uğursuz oldu.')}}

async function simulateUpdate(id){
  try{
    const d=await (await fetch(`${API}/universities/${id}/simulate-update`,{method:'POST'})).json();
    if(d.status==='warning'){alert(d.message);return}
    alert(`Simulyasiya bitdi — yeni: ${d.metrics.new_added}, dəyişən sahə: ${d.metrics.updated_fields}.`);
    runPipelineRefresh(id);
  }catch(e){alert('Simulyasiya uğursuz oldu.')}
}

/* ---------- pipeline overlay animation ---------- */
function animatePipeline(){
  const stages=[...document.querySelectorAll('#pipelineStages .stage')];
  stages.forEach(s=>s.classList.remove('live','done'));
  let i=0;
  function step(){
    if(i>0)stages[i-1]?.classList.add('done');
    stages.forEach((s,k)=>{if(k<i)s.classList.add('done')});
    if(i<stages.length){stages[i].classList.remove('done');stages[i].classList.add('live');i++;
      window._pipeTimer=setTimeout(step,520);}
  }
  clearTimeout(window._pipeTimer); step();
}

window.onload=()=>{fetchUniversities();fetchPendingPrograms()};
