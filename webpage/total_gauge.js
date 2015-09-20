Gauge.prototype.Logger = Logger.get("gauge");	

Gauge.prototype.update = function update()
{
        this.Logger.debug("%s: %s", arguments.callee.name, "Starting ...");
	var value = this.getValue();
	this.redraw(value);
};

//window.wpd3.updateGauge = updateGauge;
			
Gauge.prototype.getValue = function getValue()
{
        var total = 0.0;
        for (i = 0; i < window.wpd3.idlist.length; i++) { 
            if ( window.wpd3.idlist[i].title === "Total Residential" ) {
                total += window.wpd3.idlist[i].val;
            }
        }

	return total;
};

// Added for disconnection notification - CSN
Gauge.prototype.configureNetNotify = function configureNetNotify ()
{
            this.config.twoPi = 2 * Math.PI;
            this.config.progress = 0;
            this.config.total = 100,
            this.config.formatPercent = d3.format(".0%");

            this.config.arc = d3.svg.arc()
                .startAngle(0)
                .innerRadius(window.wpd3.config_gauge.radius*.9)
                .outerRadius(window.wpd3.config_gauge.radius)
                ;
};
	
Gauge.prototype.renderNetNotify = function renderNetNotify()
{
            this.meter = this.body.append("g")
                .style("opacity", "0")
                .attr("class", "progress-meter")
                .attr("transform", "translate(" + this.config.size / 2 + "," + this.config.size / 2 + ")");

            this.meter.append("path")
                .attr("class", "progress-meter-background")
                .attr("d", this.config.arc.endAngle(this.config.twoPi));

           this.foreground = this.meter.append("path")
               .attr("class", "progress-meter-foreground");

	   this.meter.append("circle")
		//.attr("cx", this.config.cx)
		//.attr("cy", this.config.cy)
		.attr("r", 0.9 * this.config.radius)
		.style("fill", "#fff")
		.style("stroke", "#e0e0e0")
		.style("stroke-width", "0px");

           this.text = this.meter.append("text")
               .attr("text-anchor", "middle")
               .attr("class", "progress-meter-text");

           this.text2 = this.meter.append("text")
               .attr("y", 40)
               .attr("text-anchor", "middle")
               .attr("class", "progress-meter-text2");

           this.text.text('No Data Link');
           this.text2.text('Reconnecting ...');
};

Gauge.prototype.opacityNetNotify = function opacityNetNotify(incr)
{
            var opacity = parseFloat(this.meter.style("opacity"));

            if (opacity < 1.0 )
            {
               opacity = opacity + incr;
            }
            this.meter.style("opacity", opacity);
            //this.Logger.debug(arguments.callee.name + ": " + opacity + " Incr: " + incr);
};

Gauge.prototype.endNetNotify = function endNetNotify() {
            this.meter
               .style("opacity", 0)
               .style("visibility", "hidden");
};


Gauge.prototype.animateNetNotify = function animateNetNotify(percentage, over){
            this.meter
                .style("visibility", "visible");
            this.opacityNetNotify(.1);

            var i = d3.interpolate(this.config.progress, percentage);
            //var j = d3.interpolate(percentage, this.config.progress);

            d3.transition().duration(over).tween("progress", function () {
                return function (t) {
                    window.wpd3.gauge.opacityNetNotify(.1);

                    if ( t < .5)
                    {
                        progress = i(t*2);
                    }
                    else
                    {
                        progress = i((1-t)*2);
                    }
                    window.wpd3.gauge.foreground.attr("d", window.wpd3.gauge.config.arc.endAngle(window.wpd3.gauge.config.twoPi * progress));

                    var x = t % .2;
                    var opacity = 0;
                    if ( x < .1) opacity = (.1-x)*10;
                    else opacity = (x-.1)*10;
                    window.wpd3.gauge.text.style("opacity", opacity);
                    //window.wpd3.gauge.text.text(window.wpd3.gauge.config.formatPercent(progress));
                    //if (t == 1) window.wpd3.gauge.meter.style("visibility", "hidden");
                };
            });
}; 
