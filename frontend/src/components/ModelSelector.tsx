import type {ModelOption} from '../types';

export default function ModelSelector({models, value, disabled, onChange}: {
  models: ModelOption[];
  value: string;
  disabled: boolean;
  onChange: (model: string) => void;
}) {
  return <label className="model-picker" htmlFor="ai-model"><span>AI model</span>
    <select id="ai-model" value={value} disabled={disabled} onChange={event => onChange(event.target.value)}>
      {!models.length && <option value="">Connect the backend to choose a model</option>}
      {models.map(model => <option key={model.id} value={model.id}>{model.label}</option>)}
    </select>
  </label>;
}
