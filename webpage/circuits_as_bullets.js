function CircuitsAsBullets(placeholder, cfg)
{
    //var self = this;  // internal d3 functions

    this.placeholder = placeholder;
    this.cfg = cfg;

    this.Logger = Logger.get('circuits_as_bullets');

    this._toggle = {};

    this.margin = {top: 5, right: 40, bottom: 20, left: 150};
    this.width = this.cfg.width - this.margin.left - this.margin.right;
    this.height = 50 - this.margin.top - this.margin.bottom;

    this.chart = d3.bullet()
        .width(this.width)
        .height(this.height);

    this.Logger.debug(arguments.callee.name + ": Starting ...");

    this.toggleRelay = function toggleRelay() {
        //var _id = new String(this.id);

        var _target = d3.event.target.id;
        var _target = _target.split(" ");
        var _id = _target[0];
        var _placeholder = _target[1];

        // HACK - NOT SURE HOW TO DO THIS FROM EVENT? - CSN
        _this = window.wpd3.tabs[_placeholder];

        _this.Logger.debug("%s: click ... %s", arguments.callee.name, _id + _placeholder);

        _this._toggle[_id].style("stroke", "steelblue");

        if ( _this.cfg[_id].relay )
        {
            mqtt.publish(mqtt.topic+'_RCV/ctl/'+ _id +'relay','0');
        }
        else
        {
            mqtt.publish(mqtt.topic+'_RCV/ctl/'+ _id +'relay','1');
        }

        _this.Logger.debug("%s: clicked ... %s", arguments.callee.name, _id);
    }

    this.addCircuit = function addCircuit(d, _this) {
        if (_this === "undefined") _this = this;

        _this.Logger.debug(arguments.callee.name + ": " + d.id + "=" + d.val);

        var svg = d3.select("#" + _this.placeholder).selectAll("svg")
            .data(_this.cfg.bullet_list).enter()
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
            //.attr("dx", "-1em")
            .text(function(d) { return d.title; });

        title.append("rect")
                    .attr("class", "subtitleRect")
                    .attr("x", "-6em")
                    .attr("y", "0.5em")
                    .attr("width", "6em")
                    .attr("height", "1.5em")
                    .attr("rx", "0.6em")
                    .attr("ry", "0.6em");

        title.append("text")
            .attr("class", "subtitle")
            .attr("dx", "-1.5em")
            .attr("dy", "1.5em")
            .text(function(d) { return d.subtitle; });

        _this.Logger.debug(arguments.callee.name + " : relay " + d.relay);
        _this._toggle[d.id] = title.append("circle")
                    .attr("class", "subtitleCircle")
                    .attr("context", _this)
                    .attr("id", d.id + " " + _this.placeholder + " toggle")
                    .attr("cx", "-5.5em")
                    //.attr("cx", "-0.5em")
                    .attr("cy", "1.25em")
                    .attr("stroke", "black")
                    .attr("stroke-width","2")
                    .attr("r", "0.6em")
                    .attr("class", "subtitleToggleRelay")    // style the legend
                    .on("click", _this.toggleRelay)
                    .style("fill", (d.relay === 0 ? "green" : "red"));

        _this.Logger.debug(arguments.callee.name + " : Finished");
    };

    this.update = function update(_idlist, _this) {
        _this.Logger.debug(arguments.callee.name + ": Starting ... " + _idlist + " " + _this);

        if (_this === "undefined" ) _this = this;

        if ( typeof _this.cfg.bullet_list === "undefined" )
        {
            _this.cfg.bullet_list = [];
        }

        _idlist.forEach(function (_id) {
            d = _this.cfg[_id];
            d.measures = [ d.val ];

            if ( typeof d["subtitle"] === "undefined" || d["subtitle"] === "???" )
            {
                // this is not a kwatt reading ... what is it?
                _this.Logger.warn(arguments.callee.name + ": Not a kw reading for " + d.id + "-" + d["subtitle"]); 
            }
            else if (typeof d[_this.placeholder] === "undefined")
            {
                // have we dealt with this id before?
                _this.Logger.debug("first time looking at " + _id + ":" + d.id);

                // NO .. setup this id the first time through
                d[_this.placeholder] = true;
                d.markers = [ d.val ];
                _this.cfg.bullet_list.push(d);
                _this.addCircuit(d, _this);
            }
            else
            {
                _this.Logger.debug("Updating " + _id + ":" + d.ranges);
                if ( d.markers[0] < d.val )
                {
                    d.markers = [ d.val ];
                }

                _this._toggle[d.id]
                    .style("fill", (d.relay === 0 ? "green" : "red"))
                    .style("stroke", "black");
                    //.style("cx", (d.relay === 0 ? "-5.5em" : "-0.5em"));

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
