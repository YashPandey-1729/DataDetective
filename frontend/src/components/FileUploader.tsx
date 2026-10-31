import {useRef, useState} from 'react';
import {UploadCloud, ImagePlus, LoaderCircle} from 'lucide-react';
export default function FileUploader({image = false, busy, disabled = false, onFile}: {image?: boolean; busy: boolean; disabled?: boolean; onFile: (file: File) => void}) {
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  return <div className="upload-control"><input ref={input} type="file" hidden disabled={busy || disabled} accept={image ? '.png,.jpg,.jpeg' : '.csv,.xlsx,.xls'} onChange={e => {if (!busy && !disabled && e.target.files?.[0]) onFile(e.target.files[0]); e.target.value = '';}}/>
    <button type="button" className={`dropzone ${image ? 'image-drop' : ''} ${drag ? 'dragging' : ''}`} disabled={busy || disabled} aria-busy={busy}
    onClick={() => input.current?.click()} onDragOver={e => {e.preventDefault(); if (!busy && !disabled) setDrag(true);}} onDragLeave={() => setDrag(false)}
    onDrop={e => {e.preventDefault(); setDrag(false); if (!busy && !disabled && e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]);}}>
    <span className="upload-icon">{busy ? <LoaderCircle className="spin"/> : image ? <ImagePlus/> : <UploadCloud/>}</span>
    <strong>{busy ? 'Reading your file…' : image ? 'Add a chart screenshot' : 'Drop your dataset here'}</strong>
    <span>{image ? 'Give the investigator visual context · PNG, JPG · 5 MB' : 'or click to browse · CSV, Excel · up to 15 MB'}</span>
  </button></div>;
}
