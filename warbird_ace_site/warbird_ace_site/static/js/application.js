(() => {
  const form = document.getElementById('sacForm');
  if (!form) return;
  const statusBox = document.getElementById('statusBox');
  const previewBtn = document.getElementById('previewBtn');
  const submitBtn = document.getElementById('submitBtn');
  const modal = document.getElementById('successModal');
  const submissionId = document.getElementById('submissionId');
  const downloadBtn = document.getElementById('downloadBtn');
  let lastPdfBlob = null;

  const exp = document.getElementById('experienceRows');
  for (let i = 0; i < 7; i++) {
    const row = document.createElement('div');
    row.className = 'experience-row';
    row.innerHTML = `<input name="exp_site_${i}" aria-label="Show name or practice site row ${i+1}"><input type="date" name="exp_date_${i}" aria-label="Date row ${i+1}"><input type="checkbox" name="exp_show_${i}" aria-label="Show row ${i+1}"><input type="checkbox" name="exp_practice_${i}" aria-label="Practice row ${i+1}">`;
    exp.appendChild(row);
  }

  const pads = {};
  function setupPad(id) {
    const canvas = document.getElementById(id), ctx = canvas.getContext('2d');
    ctx.lineWidth = 3; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = '#111';
    let drawing = false, hasInk = false;
    const pos = e => { const r=canvas.getBoundingClientRect(), p=e.touches?e.touches[0]:e; return {x:(p.clientX-r.left)*(canvas.width/r.width), y:(p.clientY-r.top)*(canvas.height/r.height)}; };
    const start=e=>{e.preventDefault();drawing=true;const p=pos(e);ctx.beginPath();ctx.moveTo(p.x,p.y)};
    const move=e=>{if(!drawing)return;e.preventDefault();const p=pos(e);ctx.lineTo(p.x,p.y);ctx.stroke();hasInk=true};
    const end=e=>{if(drawing)e.preventDefault();drawing=false};
    canvas.addEventListener('pointerdown', start); canvas.addEventListener('pointermove', move); window.addEventListener('pointerup', end);
    pads[id]={canvas,clear:()=>{ctx.clearRect(0,0,canvas.width,canvas.height);hasInk=false},data:()=>hasInk?canvas.toDataURL('image/png'):''};
  }
  setupPad('applicantPad'); setupPad('evaluatorPad');
  document.querySelectorAll('[data-clear]').forEach(b=>b.addEventListener('click',()=>pads[b.dataset.clear].clear()));

  document.querySelectorAll('[data-jump]').forEach(btn => btn.addEventListener('click', () => document.getElementById(btn.dataset.jump)?.scrollIntoView({behavior:'smooth'})));
  const observer = new IntersectionObserver(entries => { entries.forEach(e => { if(e.isIntersecting){ document.querySelectorAll('.progress-rail button').forEach(b=>b.classList.toggle('active', b.dataset.jump===e.target.id)); } }); }, {rootMargin:'-25% 0px -65% 0px'});
  document.querySelectorAll('.form-section').forEach(s=>observer.observe(s));

  function collect() {
    const fd = new FormData(form), data = {};
    for (const [k,v] of fd.entries()) data[k]=v;
    form.querySelectorAll('input[type=checkbox]').forEach(c=>data[c.name]=c.checked);
    data.experience=[];
    for(let i=0;i<7;i++){const site=data[`exp_site_${i}`]||'', date=data[`exp_date_${i}`]||'', show=!!data[`exp_show_${i}`], practice=!!data[`exp_practice_${i}`]; if(site||date||show||practice)data.experience.push({site,date,show,practice}); delete data[`exp_site_${i}`];delete data[`exp_date_${i}`];delete data[`exp_show_${i}`];delete data[`exp_practice_${i}`];}
    data.applicant_signature=pads.applicantPad.data(); data.evaluator_signature=pads.evaluatorPad.data();
    return data;
  }

  function base64ToBlob(b64){const bin=atob(b64), bytes=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)bytes[i]=bin.charCodeAt(i);return new Blob([bytes],{type:'application/pdf'});}
  function openPdf(blob){const u=URL.createObjectURL(blob);window.open(u,'_blank','noopener');setTimeout(()=>URL.revokeObjectURL(u),120000);}
  function setStatus(msg, cls=''){statusBox.className='status-box '+cls;statusBox.textContent=msg;}

  previewBtn.addEventListener('click', async () => {
    setStatus('Generating preview…','working'); previewBtn.disabled=true;
    try{const res=await fetch('/api/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(collect())});const out=await res.json();if(!res.ok)throw new Error(out.error||'Preview failed');openPdf(base64ToBlob(out.pdf_base64));setStatus('Preview generated. Review the PDF before submitting.');}catch(e){setStatus(e.message,'error')}finally{previewBtn.disabled=false;}
  });

  form.addEventListener('submit', async e => {
    e.preventDefault();
    if(!form.reportValidity()) return;
    const data=collect();
    if(!data.applicant_signature){setStatus('Applicant signature is required.','error');document.getElementById('signatures').scrollIntoView({behavior:'smooth'});return;}
    if(!data.evaluator_signature){setStatus('Evaluator signature is required.','error');document.getElementById('signatures').scrollIntoView({behavior:'smooth'});return;}
    setStatus('Generating and sending the completed application…','working'); submitBtn.disabled=true; previewBtn.disabled=true;
    try{const res=await fetch('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const out=await res.json();if(!res.ok)throw new Error(out.error||'Submission failed');lastPdfBlob=base64ToBlob(out.pdf_base64);submissionId.textContent=out.application_id;modal.hidden=false;setStatus('Application submitted successfully.');}catch(err){setStatus(err.message,'error');}finally{submitBtn.disabled=false;previewBtn.disabled=false;}
  });

  downloadBtn.addEventListener('click',()=>{if(!lastPdfBlob)return;const a=document.createElement('a');a.href=URL.createObjectURL(lastPdfBlob);a.download=`SAC_${submissionId.textContent}.pdf`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),30000);});
})();
