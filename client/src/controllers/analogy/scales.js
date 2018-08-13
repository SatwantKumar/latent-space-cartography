import * as d3 from 'd3'
import _ from 'lodash'

/**
 * @fileOverview
 * Creates and holds all the scales in analogy scatter plot.
 */
class Scales {
  /**
   * Constructor
   * @param data
   * @param params
   */
  constructor (data, params) {
    /**
     * Public parameters
     */
    this.outerWidth = params.outerWidth
    this.outerHeight = params.outerHeight
    this.margin = params.margin
    this.chart_type = params.chart_type
    this.y_field = params.y_field

    /**
     * Scales
     */
    this.initialX = null
    this.initialY = null

    this.x = null
    this.y = null

    /**
     * Initialize
     */
    this.init(data)
  }

  /**
   * Initialize the scales for scatter plot
   * @param data
   * @private
   */
  _initScatterScales (data) {
    // create x and y plotting fields so we can unify the code
    for (let i = 0; i < data.length; i++) {
      data[i]._x = data[i].x
      data[i]._y = data[i][this.y_field]
    }

    // create the scales
    let x = d3.scaleLinear()
      .range([0, this.width()]).nice()

    let y = d3.scaleLinear()
      .range([this.height(), 0]).nice()

    let xMax = d3.max(data, (d) => d._x) * 1.05
    let xMin = d3.min(data, (d) => d._x) * 1.05
    let yMax = d3.max(data, (d) => d._y) * 1.05
    let yMin = d3.min(data, (d) => d._y) * 1.05

    x.domain([xMin, xMax])
    y.domain([yMin, yMax])

    this.x = x
    this.y = y
  }

  /**
   * Initialize the scales for bee swarm plots
   * @param data
   * @private
   */
  _initSwarmScales (data) {
    // x scale is still a continuous linear scale
    let x = d3.scaleLinear()
      .range([0, this.width()]).nice()
      .domain(d3.extent(data, (d) => d.x))

    // make a "identity" x and y scale for interfacing purpose
    this.x = d3.scaleLinear()
      .range([0, this.width()])
      .domain([0, this.width()])
    this.y = d3.scaleLinear()
      .range([0, this.height()])
      .domain([0, this.height()])

    // this is a temporary scale that maps category to height
    let y = d3.scaleBand().rangeRound([0, this.height()]).padding(0.1)
      .domain(data.map((d) => d[this.y_field]))

    // simulate bee swarm
    _.each(y.domain(), (cat) => {
      let dd = _.filter(_.map(data, (d, idx) => {
        return {i: idx, x: d.x, y: d[this.y_field]}
      }), (d) => d.y === cat)

      let h = y(cat)
      let simulation = d3.forceSimulation(dd)
        .force('x', d3.forceX((d) => x(d.x)).strength(1))
        .force('y', d3.forceY(h).strength(0.1))
        .force('collide', d3.forceCollide(3))
        .stop()

      for (let i = 0; i < 40; i++) {
        simulation.tick()
      }

      _.each(dd, (d) => {
        data[d.i]._x = d.x
        // TODO: why does '' has weird y value?
        data[d.i]._y = _.isNaN(this.y(d.y)) ? 0 : d.y
      })
    })

    console.log(d3.extent(data, (d) => d.x))
    console.log(d3.extent(data, (d) => x(d.x)))
    console.log(d3.extent(data, (d) => d._x))
  }

  /**
   * Initialize: create the scales
   * @param data
   */
  init (data) {
    if (this.chart_type === 1) {
      this._initScatterScales(data)
    } else {
      this._initSwarmScales(data)
    }

    this.initialX = this.x.copy()
    this.initialY = this.y.copy()
  }

  /**
   * A helper function to get the canvas width (outer minus margin)
   */
  width () {
    return this.outerWidth - this.margin.left - this.margin.right
  }

  /**
   * A helper function to get the canvas height (outer minus margin)
   */
  height () {
    return this.outerHeight - this.margin.top - this.margin.bottom
  }
}

export default Scales
