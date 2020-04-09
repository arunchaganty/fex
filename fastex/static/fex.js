// region: Utility functions
function resize(obj) {
  obj.style.height = obj.contentWindow.document.body.scrollHeight + 'px';
}

function split( val ) {
  return val.split( /,\s*/ );
}

function extractLast( term ) {
  return split( term ).pop();
}

function addInputGroup(label, input) {
  let ret = $("<div class='input-group mb-2'></div>");
  if (label !== undefined) ret.append(label);
  ret.append(input);
  return ret;
}
// endregion

/**
 * ViewInterface renders multiple widgets in the main block and allows users to
 * select which range of widgets to render through the nav-bar
 */
class ViewInterface {
  /**
   * Constructs a view interface
   * @param elem - the root element to draw the interface in
   * @param nav - the navbar element
   */
  constructor(elem, nav, rangeCount) {
    if (rangeCount == null) rangeCount = 10;

    this.elem = $(elem);
    this.nav = $(nav);
    // The range of elements to render.
    this.range = [0, rangeCount];
    // The total number of elements.
    this.count = 0;
  }

  init() {
    // Hook up callbacks.
    this._setupCallbacks();
    this.updateCount();

    const [lower, upper] = this.range;
    const count = upper - lower;
    this.updateRange(lower, count);
  }

  _setupCallbacks() {
    const self = this;
    this.nav.find("#nav-prev").on("click", () => self.prev());
    this.nav.find("#nav-next").on("click", () => self.next());
    this.nav.find("#nav-range").on("change", (evt) => {
      const value = evt.target.value;
      const parts = value.split("-");
      console.assert(parts === 2);
      const [lower, upper] = [Number.parseInt(parts[0])-1, Number.parseInt(parts[1])];
      const count = upper - lower;
      self.updateRange(lower, count);
    });

    $('body').on("keydown", evt => {
      console.log(evt.key);
      if (evt.key === "ArrowLeft") self.prev();
      else if (evt.key === "ArrowRight") self.next();
    });
  }

  next() {
    const self = this;
    const [lower, upper] = self.range;
    const count = upper - lower;
    const newUpper = Math.min(self.count, upper+count);
    self.updateRange(Math.max(0, newUpper-count), count);
  }
  prev() {
    const self = this;
    const [lower, upper] = self.range;
    const count = upper - lower;
    const newLower = Math.max(0, lower - count);
    self.updateRange(newLower, count);
  }


  updateCount() {
    // Set up count in nav interface.
    const self = this;
    $.ajax({
      url: "/count/",
      contentType: "application/json",
      method: "GET",
      success: function(data) {
        // Clear root.
        self.count = data.value;
        self.nav.find("#nav-count").text("of " + self.count);
      }
    });
  }

  renderTemplate(idx, body) {
    const ret = $("#templates").find("div.card").clone();
    ret.attr("id", "obj-" + idx);
    ret.find("h6.card-header").text("Element: " + (idx+1));
    ret.find("div.card-body").html(body);

    return ret;
  }

  updateRange(start, count) {
    const self = this;
    // Handle arguments.
    if (count == null) count = 10;
    if (start == null) start = 0;

    // Get renderables from the server.
    $.ajax({
      url: "/render/",
      contentType: "application/json",
      method: "GET",
      data: {start: start, count: count},
      success: function(data) {
        // Clear root.
        self.elem.empty();
        for (let i = 0; i < data.html.length; i++)  {
          const html = self.renderTemplate(start + i, data.html[i]);
          self.elem.append(html);
        }
        self.nav.find("#nav-range").val((start+1) + "-" + (start+count));
        self.range = [start, start+count];
      }
    });
  }
}

// Widgets
class Button {
  constructor(name, isSubmit) {
    this.name = name;
    this.isSubmit = isSubmit || false;
    this.handleClick = this.handleClick.bind(this);
    this.listeners = [];
  }

  handleClick(evt) {
    console.log(evt);
    this.listeners.forEach(listener => listener(true));
  }

  attach(fn) {
    fn(addInputGroup(undefined,
      $('<input id="'+this.name+'" type="submit" class="btn btn-primary" value="'+this.name+'" />')
      .on("click", this.handleClick)
    ));
  }

  elem() {
    return $("#" + this.name);
  }
}

class TextWidget {
  constructor(name) {
    this.name = name;
    this.listeners = [];

    this.handleChange = this.handleChange.bind(this);
  }

  handleChange(evt) {
    let val = this.value();
    this.listeners.forEach(listener => listener(val));
  }

  attach(fn) {
    if ($("#" + this.name).length > 0) {
      console.log("Already attached " + this.name + "doing nothing.");
      return;
    }
    const self = this;

    let obj = addInputGroup(
      undefined,
      // $("<label for='"+this.name+"'>"+this.name+"</label>"),
      $("<textarea id='"+this.name+"' class='form-control' placeholder='type " + this.name + "(s) here'></textarea>")
        .on("change", this.handleChange)
    );
    fn(obj);
  }

  elem() {
    return $("#" + this.name);
  }

  value() {
    let terms = split(this.elem().val());
    return terms;
  }

  setValue(val) {
    this.elem().val(val);
  }

  clear() {
    this.setValue("");
  }

  dirty() {}
}


class MultiLabelWidget {
  constructor(name) {
    this.name = name;
    this._choices = [];
    this._dirty = true;
    this.listeners = [];

    this.handleChange = this.handleChange.bind(this);
  }

  handleChange(evt) {
    let val = this.value();
    this.listeners.forEach(listener => listener(val));
  }

  dirty() {
    this._dirty = true;
  }

  attach(fn) {
    if ($("#" + this.name).length > 0) {
      console.log("Already attached " + this.name + "doing nothing.");
      return;
    }
    const self = this;

    let obj = addInputGroup(
      undefined,
      // $("<label for='"+this.name+"'>"+this.name+"</label>"),
      $("<input type='text' id='"+this.name+"' class='form-control' placeholder='type " + this.name + "(s) here' />")
        // don't navigate away from the field on tab when selecting an item
        .on( "keydown", function( event ) {
          if ( event.keyCode === $.ui.keyCode.TAB &&
              $( this ).autocomplete( "instance" ).menu.active ) {
            event.preventDefault();
          }
        })
        .on("change", this.handleChange)
        .autocomplete({
          minLength: 0,
          source: function( request, response ) {
            const term = extractLast(request.term);
            self.choices(choices => response($.ui.autocomplete.filter(choices, term)));
          },
          focus: function() {
            // prevent value inserted on focus
            return false;
          },
          select: function( event, ui ) {
            var terms = split( this.value );
            // remove the current input
            terms.pop();
            // add the selected item
            terms.push( ui.item.value );
            // add placeholder to get the comma-and-space at the end
            terms.push( "" );
            this.value = terms.join( ", " );
            return false;
          }
        })
    );
    fn(obj);
  }

  choices(fn) {
    let self = this;
    if (this._dirty) {
      // delegate back to autocomplete, but extract the last term
      $.ajax({
        url: "/autocomplete/",
        dataType: "json",
        data: {
          name: self.name,
        },
        success: function(data) {
          self._choices = data;
          self._dirty = false;
          console.log(self._choices);
          fn(self._choices);
        }
      });
    } else {
      console.log(self._choices);
      fn(self._choices);
    }
  }

  elem() {
    return $("#" + this.name);
  }

  value() {
    let terms = split(this.elem().val());
    return terms;
  }

  setValue(vs) {
    console.log(vs);
    this.elem().val(vs.join( ", " ));
  }

  clear() {
    this.setValue([]);
  }
}

class ProgressBar {
  constructor() {
    this._dirty = true;
    this._limit = 1;

    this.handleChange = this.handleChange.bind(this);
    this.listeners = [];
  }

  limit(fn) {
    let self = this;

    if (this._dirty) {
      $.ajax({
        url: "/count/",
        dataType: "json",
        data: {},
        success: function(data) {
          self._limit = data;
          self._dirty = false;
          fn(self._limit);
        }
      });
    } else {
      fn(self._limit);
    }
  }

  attach(fn) {
    if ($("#progress").length > 0) {
      console.log("#progress already attached");
      return;
    }

    fn(addInputGroup(
      $("<label for='range'>Element #<span id='progress-idx'>1</span></label>"),
      $("<input type='range' class='custom-range' id='progress' min='1' max='1' value='1' />")
        .on("input", this.handlePreviewChange)
        .on("change", this.handleChange)
    ))

    // Get the limit async
    this.limit(val => $("#progress").attr("max", val));
  }
  handlePreviewChange(evt) {
    const idx = evt.target.value;
    $('span#progress-idx').innerText = idx;
  }
  handleChange(evt) {
    this.listeners.forEach(listener => listener(Number.parseInt(evt.target.value)));
  }

  elem() {
    return $("#progress");
  }

  value() {
    return  Number.parseInt(this.elem().val());
  }

  setValue(val) {
    this.elem().val(val);
  }

  clear() {
    this.setValue(1);
  }
}

class LabelInterface extends ViewInterface {
  /**
   * Constructs a view interface
   * @param elem - the root element to draw the interface in
   * @param annotations - the root element to draw the annotation widgets in
   * @param nav - the navbar element
   */
  constructor(elem, annotations, nav) {
    super(elem, nav, 1);
    this.annotations = $(annotations);
  }

  init() {
    // Hook up callbacks.
    this.updateSchema();
    super.init();
  }

  // TODO: Change load hooks
  // TODO: Change save hooks
  // TODO: Add change listeners.

  renderSchemaElement(key, elem) {
    // Figure out which schema element we should use.
    const ret = $("#templates").find(`div.annotation-${elem["type"]}`).clone();
    ret.attr("id", `annotation-${key}`);
    ret.find("label").text(key);

    return ret;
  }

  updateSchema() {
    const self = this;
    $.ajax({
      url: "/schema/",
      contentType: "application/json",
      method: "GET",
      success: function(schema) {
        // Clear our widgets
        self.widgets = {};
        const body = self.annotations.find("div.card-body");

        // Clear the body field;
        body.html("");
        for (let key of Object.keys(schema)) {
          const elem = self.renderSchemaElement(key, schema[key]);
          if (schema[key].type === "classification") {
            self.widgets[key].push(new ClassificationWidget(elem));
          } else if (schema[key].type === "text") {
            self.widgets[key].push(new TextWidget(elem));
          } else {
            console.error("Could not add widget for type " + schema[key].type);
          }
          body.append(elem);
        }
      }
    });
    return;
    self.submit.listeners.push(submit => {
      if (!submit) return;

      let blob = {};
      blob["_idx"] = self.progress.value() - 1;
      for (let widget of self.widgets) {
        blob[widget.name] = widget.value();
      }
      console.log(blob);

      $.ajax({
        url: "/update/",
        contentType: "application/json",
        method: "post",
        data: JSON.stringify(blob),
        dataType: "json",
        success: function(data) {
          self.widgets.forEach(w => w.dirty());
          self.setIdx(self.progress.value() + 1);
        }
      });
    });
  }
}
