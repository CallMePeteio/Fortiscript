var svg;


let GREEN = "#1E8C45"
let RED = "#EA1827"



const degsToRads = deg => (deg * Math.PI) / 180.0;

function makeColorGood(svg, intensity){
    const defs = svg.append('defs');

    // Define dynamic gradients for color transitions
    const greenGradient = defs.append('linearGradient')
        .attr('id', 'greenGradient');
    greenGradient.append('stop')
        .attr('offset', '0%')
        .attr('stop-color', '#1E8C45')
        .attr('stop-opacity', 1);
    greenGradient.append('stop')
        .attr('offset', '100%')
        .attr('stop-color', d3.interpolate('#1E8C45', '#3FAE78')(intensity))
        .attr('stop-opacity', 1);

    const redGradient = defs.append('linearGradient')
        .attr('id', 'redGradient');
    redGradient.append('stop')
        .attr('offset', '0%')
        .attr('stop-color', '#EA1827')
        .attr('stop-opacity', 1);
    redGradient.append('stop')
        .attr('offset', '100%')
        .attr('stop-color', d3.interpolate('#EA1827', '#FF6347')(intensity))
        .attr('stop-opacity', 1);



    return svg
}

function drawProgress(segmentsGreen, segmentsRed,  removeDeg, intensity=1.4) {
    // Remove any existing svg for a fresh start
    d3.select("svg").remove();

    let wrapper = document.getElementById('radialprogress');

    let strokeWith = 0.5;

    let innerRadius = 90
    let radius = 110;
    let border = 12;
    let end = 1;

    let startDeg = removeDeg/2
    let rotationDeg = startDeg + 180

    let segments = segmentsRed + segmentsGreen
    let fullCircle = (2 * Math.PI) - degsToRads(removeDeg) ;
    let segmentGap = 0.002 // Gap between segments in radians
    let segmentLength = (fullCircle - segments * segmentGap) / segments;


    // Setup SVG wrapper
    svg = d3.select(wrapper)
        .append('svg')
        .attr('width', (radius + strokeWith) * 2)
        .attr('height', (radius + strokeWith) * 2)
        .attr('shape-rendering', 'geometricPrecision')
        .append('g')
        .attr('transform', `translate(${radius + strokeWith*2},${radius + strokeWith*2}) rotate(${rotationDeg})`);

    

    svg = makeColorGood(svg, intensity);
    
    let arc = d3.svg.arc()
        .innerRadius((innerRadius + strokeWith/2) - border)
        .outerRadius((radius + strokeWith/2))

    for (let i=0; i<segments; i++){
        let startAngle = i * (segmentLength + segmentGap + startDeg);
        let endAngle = startAngle + segmentLength + startDeg;

        svg.append("path")
            .datum({startAngle: i * (segmentLength + segmentGap), endAngle: (i + 1) * (segmentLength + segmentGap) - segmentGap})
            .style('fill', '#ccc')
            .attr('d', arc)
            .attr('stroke', 'black')
            .attr('stroke-width', strokeWith.toString() + "px");
    }   
    
    // Draw each segment of the progress
    var progressSegments = Math.ceil(end * segments);



    for (let i = 0; i < progressSegments; i++) {
        let startAngle = i * (segmentLength + segmentGap + startDeg);
        let endAngle = startAngle + segmentLength + startDeg;

        let path = svg.append('path')
            .datum({startAngle: i * (segmentLength + segmentGap), endAngle: (i + 1) * (segmentLength + segmentGap) - segmentGap})
            .attr('d', arc)
            .attr('stroke', 'black')
            .attr('stroke-width', strokeWith.toString() + "px");

            if (i < segmentsGreen){
                path.style('fill', (d, i) => i < segmentsGreen ? 'url(#greenGradient)' : 'url(#greenGradient)');
            }else{
                path.style('fill', (d, i) => i < redGradient ? 'url(#redGradient)' : 'url(#redGradient)');
            }
    }
}
$(document).ready(function() {
    drawProgress(8, 4, 100); 
});
