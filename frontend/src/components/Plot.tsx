// The distribution bundle avoids importing Plotly source modules at runtime.
import createPlotlyComponent from 'react-plotly.js/factory';
// @ts-expect-error Plotly distribution has no bundled TypeScript declaration.
import Plotly from 'plotly.js-dist-min';
import type {Chart} from '../types';
const Plot = createPlotlyComponent(Plotly);
export default function ChartPlot({chart}: {chart: Chart}) {
  return <Plot data={chart.data} layout={{...chart.layout, autosize:true, height:310, paper_bgcolor:'transparent', plot_bgcolor:'transparent', font:{color:'#98a6bc',family:'Segoe UI, sans-serif',size:11}, margin:{l:64,r:28,t:20,b:65}, xaxis:{...chart.layout.xaxis,gridcolor:'#202c3f',zerolinecolor:'#202c3f'},yaxis:{...chart.layout.yaxis,gridcolor:'#202c3f',zerolinecolor:'#33445e'}, hoverlabel:{bgcolor:'#172337'}, colorway:['#56d8e4','#7995ff','#b194ef']}} config={{responsive:true,displaylogo:false,modeBarButtonsToRemove:['lasso2d','select2d']}} useResizeHandler style={{width:'100%'}}/>;
}
