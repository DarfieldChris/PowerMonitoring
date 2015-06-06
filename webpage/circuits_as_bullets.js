function CircuitsAsBullets(placeholder, cfg)
{
    //var self = this;  // internal d3 functions

    this.placeholder = placeholder;
    this.cfg = cfg;

    this.Logger = Logger.get('circuits_as_bullets');

    this.margin = {top: 5, right: 40, bottom: 20, left: 120};
    this.width = this.cfg.width - this.margin.left - this.margin.right;
    this.height = 50 - this.margin.top - this.margin.bottom;

    this.chart = d3.bullet()
        .width(this.width)
        .height(this.height);

    this.Logger.debug(arguments.callee.name + ": Starting ...");

    this.addCircuit = function addCircuit(d, _this) {
        if (_this === "undefined") _this = this;

        _this.Logger.debug(arguments.callee.name + ": " + d.val);

        var svg = d3.select("#" + _this.placeholder).selectAll("svg")
            .data(_this.cfg.idlist).enter()
            .append("svg")
                .attr("id", function(d) {return d.id;})
                .attr("class", "bullet")
                .attr("width", _this.width + _this.margin.left + _this.margin.right)
                .attr("height", _this.height + _this.margin.top + _this.margin.bottom)
            .append("g")
                .attr("transform", "translate(" + _this.margin.left + "," + _this.margin.top + ")")
                .call(_this.chart);

        var title = svg.append("g")
            .style("text-anchor", "end")
            .attr("transform", "translate(-6," + _this.height / 2 + ")");

        title.append("text")
            .attr("class", "title")
            .text(function(d) { return d.title; });

        title.append("text")
            .attr("class", "subtitle")
            .attr("dy", "1em")
            .text(function(d) { return d.subtitle; });

        _this.Logger.debug(arguments.callee.name + " : Finished");
    };

    this.update = function update(_idlist, _this) {
        _this.Logger.debug(arguments.callee.name + ": Starting ... " + _idlist + " " + _this);

        if (_this === "undefined" ) _this = this;
 
        _idlist.forEach(function (_id) {
            d = _this.cfg[_id];
            d.measures = [ d.val ];

            // have we dealt with this id before?
            if (typeof d[_this.placeholder] === "undefined")
            {
                _this.Logger.debug("first time looking at " + _id + ":" + d.id);

                // NO .. setup this id the first time through
                d[_this.placeholder] = true;
                d.markers = [ d.val ];
                _this.addCircuit(d, _this);
            }
            else
            {
                _this.Logger.debug("Updating " + _id + ":" + d.ranges);
                if ( d.markers[0] < d.val )
                {
                    d.markers = [ d.val ];
                }

                var svg = d3.select("#" + _this.placeholder).selectAll("svg");
                _this.Logger.debug("Been HERE " + _id + ":" + d.ranges);
                svg.datum(_this.randomize).call(_this.chart.duration(1000));
            }
        });
    };



    this.randomize = function randomize(d) {
        return d;
    }

    this.Logger.debug(arguments.callee.name + ": Done");
}
