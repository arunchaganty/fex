class LabelInterface {
  constructor(elem, nav) {
    this.elem = $(elem);
    this.nav = $(nav);
    this.index = 0;
    this.count = 0;
    this.schema = null;

    this.value = null;
    this._bindings = {};
    this._dirty = false;
  }
  init() {
    this.updateSchema();
    this.updateCount();

    // Hook up callbacks.
    this._setupCallbacks();

    this.updateIndex();
  }

  _setupCallbacks() {
    const self = this;
    $("#nav-prev").on("click", () => self.prev());
    $("#nav-next").on("click", () => self.next());
    $("#nav-range").on("change", (evt) => {
      const value = Number.parseInt(evt.target.value);
      self.updateIndex(value);
    });

    // Construct mappings to field change
    $('body').on("keydown", evt => {
      if (evt.key === "ArrowLeft") self.prev();
      else if (evt.key === "ArrowRight") self.next();
      else if (self._bindings[evt.key] != null) self._bindings[evt.key]();
    });
  }

  next() {
    if (this.index < this.count-1) {
      this.updateIndex(this.index + 1);
    }
  }
  prev() {
    if (this.index > 0) {
      this.updateIndex(this.index - 1);
    }
  }

  updateSchema() {
    // Set up schema in nav interface.
    const self = this;
    $.ajax({
      url: "/schema/",
      contentType: "application/json",
      method: "GET",
      success: function(data) {
        // Clear root.
        self.schema = data;
      }
    });
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
        const nav_count = $("#nav-count");
        nav_count.text("of " + self.count);
      }
    });
  }

  isComplete() {
    const anns = this.value._fex;
    for (let field in this.schema.fields) {
      if (this.schema.fields[field].optional !== true && anns[field] == null) {
        return false;
      }
    }
    return true;
  }

  handleChange(change) {
    // Change the value.
    this.value._fex[change.field] = change.value;

    // Set a dirty bit.
    this._dirty = true;

    // Check if all the required fields have been filled in. If so, move on.
    if (this.isComplete()) {
      // Auto-advance.
      this.next();
    }
  }

  renderTemplate(idx, body) {
    const self = this;
    const ret = $("#templates").find("#card").clone();
    ret.attr("id", "obj-" + idx);
    ret.find("div.card-header").text("Element: " + (idx+1));
    ret.find("div.card-body").html(body);

    // Per template field.
    const annotations = ret.find("ul.list-group.annotations");
    const ann = this.value._fex;
    for (let field in this.schema.fields) {
      const desc = this.schema.fields[field];
      let elem;
      switch (desc.type) {
        case "text": {
          elem = $("#templates").find("#text").clone();
          if (ann != null && ann[field] != null) {
            elem.find("textarea").val(ann[field]);
          }
          elem.on("change", (evt) => {
            self.handleChange({field: field, value: evt.target.value});
          });
          elem.on("keypress keydown keyup", (evt) => {
            evt.stopPropagation();
          });
          break;
        }
        case "multiclass": {
          elem = $("#templates").find("#multiclass").clone();
          const bindings = desc.bindings;

          for (let value of desc.values) {
            const btn = $("<button type='button' class='btn btn-outline-primary'>").text(value);
            // Check selected.
            if (ann != null &&
                ann[field] != null) {
                if (ann[field] == value) {
                  btn.addClass("active");
                }
            }
            if (bindings && bindings[value]) {
              let shortcut = bindings[value];
              if (shortcut == " ") {
                shortcut = "<S>";
              }
              btn.append($("<span class='badge badge-primary'>").text(shortcut));
            }
            elem.find("div").append(btn);

            const handler = () => {
              elem.find("button").removeClass("active");
              btn.addClass("active");
              self.handleChange({field: field, value: value});
            };
            btn.on("click", handler);
            if (bindings && bindings[value]) {
              self._bindings[bindings[value]] = handler;
            }
          }
          break;
        }
        default: continue;
      }
      elem.attr("id", "obj-" + idx + "-" + field);
      elem.find("label").text(field);
      annotations.append(
        $("<li class='list-group-item'></li>").append(elem)
      );
    }
    return ret;
  }

  updateIndex(index) {
    const self = this;

    // Handle arguments.
    if (index == null) index = 0;

    const doGet = () => {
      // Get renderables from the server.
      $.ajax({
        url: "/render/",
        contentType: "application/json",
        method: "GET",
        data: {start: index, count: 1},
        error: console.log,
        success: (data) => {
          // Clear root.
          self.value = data.obj[0];
          self.elem.empty();
          if (self.value._fex == null) self.value._fex = {};

          self.elem.append(self.renderTemplate(index, data.html[0]));
          self.index = index;
          self._dirty = false;

          $("#nav-range").val(index+1);
        }
      });
    };

    // First update if needed.
    if (self._dirty) {
      $.ajax({
        url: `/update/${self.index}/`,
        contentType: "application/json",
        method: "POST",
        data: JSON.stringify(self.value),
        error: console.log,
        success: () => doGet(),
      })
    } else {
      doGet();
    }

  }
}

// Only global variable -- for console debugging.
var ui = new LabelInterface(document.getElementById('root'));
ui.init();
