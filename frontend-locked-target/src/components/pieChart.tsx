import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
const multiAncestry = {
  "MAE_EUR": "European",
  "MAE_OTH": "Additional Diverse Ancestries",
  "MAE_ASN": "Additional Asian Ancestries",
 "MAE_AFR": "African",
 "MAE_EAS":"East Asian",
 "MAE_SAS":"South Asian",
 "MAE_AMR":"Hispanic or Latin American",
  "MAE_GME":"Greater Middle Eastern",
  "MAE_NR":"Not Reported",
  "MAO_EUR": "European",
    "MAO_OTH": "Additional Diverse Ancestries",
    "MAO_ASN": "Additional Asian Ancestries",
   "MAO_AFR": "African",
   "MAO_EAS":"East Asian",
   "MAO_SAS":"South Asian",
   "MAO_AMR":"Hispanic or Latin American",
    "MAO_GME":"Greater Middle Eastern",
    "MAO_NR":"Not Reported"

}

const ancestryMap = {
  "MAE":
  {
    label:"Multi-ancestry (including European)",
    color:"#f781bf"
  },
  'AFR': { 
    label: 'African',
    color: '#ffd900'
  },
  'EAS': {
    label: 'East Asian',
    color: '#4daf4a'
  },
  'SAS': {
    label: 'South Asian',
    color: '#984ea3'
  },
  "ASN":
  {
    label:"Additional Asian Ancestries",
    color:"#b15928"
  },
  'EUR': {
    label: 'European',
    color: '#377eb8'
  },
  'GME':
  {
    label:"Greater Middle Eastern",
    color:"#00ced1"
  },
  "AMR": {
    label: 'Hispanic or Latin American ',
    color: '#e41a1c'
  },
  "OTH":
  {
    label:"Additional Diverse Ancestries",
    color:"#999"
  },
  "NR":
  {
    label:"Not Reported",
    color:"#4343"
  },
  "MAO":{
    label:"Multi-ancestry (excluding European)",
    color:"#f781bf"
  }
  
  
};
// const dist = {
//   AFR: 20,
//   EAS: 20,
//   EUR: 40,
//   SAS: 20,
// };
const DonutChart = ({chartData, symbol,heading=""}) => {
  if(!chartData) return null;
  const svgRef = useRef();
  const processedData = Object.entries(chartData.dist)?.map(([code, value]) => ({
    label: ancestryMap[code]?.label || code,
    value: value,
    color: ancestryMap[code]?.color || '#999',
    code
    
  }));
  useEffect(() => {
    // Sample data
    const data =processedData

    // Set dimensions for icon size
    const width = 50;
    const height = 50;
    const margin = 2;
    const radius = Math.min(width, height) / 2 - margin;

    // Clear any existing SVG
    d3.select(svgRef.current).selectAll("*").remove();

    // Create SVG
    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .append('g')
      .attr('transform', `translate(${width / 2},${height / 2})`);

    // Create tooltip div
    const tooltip = d3.select('body').append('div')
      .attr('class', 'absolute hidden bg-black/80 text-white p-2 rounded shadow-lg text-sm')
      .style('pointer-events', 'none');

    // Set color scale
    // const color = d3.scaleOrdinal()
    //   .domain(data.map(d => d.label))
    //   .range(d3.schemeCategory10);

    // Create pie layout
    const pie = d3.pie()
      .value(d => d.value)
      .sort((a, b) => a.code.localeCompare(b.code)); 

    // Create arc generator
    const arc = d3.arc()
      .innerRadius(radius * 0.6)
      .outerRadius(radius);

    // Create the donut segments
    const paths = svg.selectAll('path')
      .data(pie(data))
      .enter()
      .append('path')
      .attr('d', arc)
      .attr('fill', d => ancestryMap[d.data.code]? ancestryMap[d.data.code].color : "black") // Always use color from ancestryMap
      .attr('stroke', 'white')
      .style('stroke-width', '1px');

    // Add center text
    svg.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('font-size', '16px')
      .attr('font-family', 'Arial, sans-serif')
      .attr('fill', '#444')
      .text(symbol);

    // Add hover interactions and tooltip
    paths
.on('mouseover', function(event, _d) {
  // Show tooltip with all values
  const tooltipContent = `
    <div class="font-bold flex items-center gap-2">
      ${heading}
    </div>
    
    <hr class="my-1 border-white/30">
    ${data.map(item => `
      <div class="flex flex-col relative my-2 ">
        <div class="flex gap-2 relative">
          <div class="absolute left-0 top-0 bottom-0 w-[5px]" style="background-color:${ancestryMap[item.code].color}"></div>
          <div class="ml-4">
  <span>${ancestryMap[item.code].label}: ${item.value}%</span>
  ${item.code === "MAE" && chartData?.multi ? `
    <div class="flex flex-col">
      <ul class="list-disc pl-6">
        ${chartData.multi
          .filter(multiItem => multiItem.startsWith("MAE")) // Filter to only include items starting with "MAE"
          .map(multiItem => `
            <li class="">
              ${multiAncestry[multiItem]}
            </li>
          `).join('')}
      </ul>
    </div>
    
  ` : ''}
  ${item.code === "MAE" && chartData?.multi ? `
    <div class="flex flex-col">
      <ul class="list-disc pl-6">
        ${chartData.multi
          .filter(multiItem => multiItem.startsWith("MAO")) // Filter to only include items starting with "MAE"
          .map(multiItem => `
            <li class="">
              ${multiAncestry[multiItem]}
            </li>
          `).join('')}
      </ul>
    </div>
    
  ` : ''}
</div>
          
          </div>
          
      </div>
     
    `).join('')}
     <hr class="my-1 border-white/30">
          ${chartData.count} ${symbol==="E"? "sample sets" : "individuals"} (100%)
  `;

  tooltip
    .html(tooltipContent)
    .classed('hidden', false)
    .style('left', (event.pageX + 10) + 'px')
    .style('top', (event.pageY + 10) + 'px');
})
.on('mousemove', function(event) {
  tooltip
    .style('left', (event.pageX + 10) + 'px')
    .style('top', (event.pageY + 10) + 'px');
})
.on('mouseout', function() {
  // Hide tooltip
  tooltip.classed('hidden', true);
});

    // Cleanup function
    return () => {
      tooltip.remove();
    };
  }, [processedData]);

  return (
    <div className="inline-block">
      <svg ref={svgRef}></svg>
    </div>
  );
};

export default DonutChart;