// UX helpers
document.addEventListener('DOMContentLoaded', ()=>{
  const input = document.getElementById('fileInput');
  const sel = document.getElementById('selectedName');
  if(!input) return;

  input.addEventListener('change', ()=>{
    if(input.files && input.files.length){
      sel.textContent = input.files[0].name + ' (' + Math.round(input.files[0].size/1024) + ' KB)';
    } else {
      sel.textContent = 'No file selected';
    }
  });

  // Drag & drop support on file-input label
  const fileInputLabel = document.querySelector('.file-input');
  if(fileInputLabel){
    ['dragenter','dragover'].forEach(ev=> fileInputLabel.addEventListener(ev, e=>{ e.preventDefault(); fileInputLabel.classList.add('drag'); }));
    ['dragleave','drop'].forEach(ev=> fileInputLabel.addEventListener(ev, e=>{ e.preventDefault(); fileInputLabel.classList.remove('drag'); }));
    fileInputLabel.addEventListener('drop', e=>{
      const dt = e.dataTransfer;
      if(dt && dt.files && dt.files.length){
        const fileInput = document.getElementById('fileInput');
        const data = new DataTransfer();
        data.items.add(dt.files[0]);
        fileInput.files = data.files;
        fileInput.dispatchEvent(new Event('change'));
      }
    });
  }
});
