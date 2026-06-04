(() => {
  const { useState: useStateN, useRef: useRefN } = React;
  function slugify(s) {
    return (s || "").trim().toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 24) || "";
  }
  const fmtMB = (bytes) => (bytes / 1e6).toFixed(1) + " MB";
  function NewRun({ onStart, busy }) {
    const [title, setTitle] = useStateN("");
    const [dramaId, setDramaId] = useStateN("");
    const [idTouched, setIdTouched] = useStateN(false);
    const [episodes, setEpisodes] = useStateN([]);
    const [mode, setMode] = useStateN("llm");
    const [drag, setDrag] = useStateN(false);
    const inputRef = useRefN(null);
    const effId = dramaId || slugify(title) || "drama";
    const renumber = (list) => list.map((e, i) => ({ ...e, epId: `${effId}_ep${String(i + 1).padStart(2, "0")}` }));
    const addFiles = (fileList) => {
      const vids = Array.from(fileList).filter((f) => /\.(mp4|mov|m4v|mkv)$/i.test(f.name) || f.type.startsWith("video"));
      const next = vids.map((f, i) => ({ key: f.name + f.size + Math.random(), name: f.name, size: f.size }));
      setEpisodes((cur) => renumber([...cur, ...next]));
    };
    const onDrop = (e) => {
      e.preventDefault();
      setDrag(false);
      if (e.dataTransfer.files) addFiles(e.dataTransfer.files);
    };
    const removeEp = (key) => setEpisodes((cur) => renumber(cur.filter((e) => e.key !== key)));
    const recall = Math.max(20, Math.min(400, Math.round(episodes.length * 4)));
    const canStart = title.trim() && episodes.length > 0 && !busy;
    const start = () => {
      if (!canStart) return;
      onStart({
        dramaId: effId,
        dramaTitle: title.trim(),
        mode,
        episodes: renumber(episodes).map((e) => ({ epId: e.epId, name: e.name, sizeMB: +(e.size / 1e6).toFixed(1) }))
      });
    };
    return /* @__PURE__ */ React.createElement("div", { className: "newrun" }, /* @__PURE__ */ React.createElement("div", { className: "nr-head" }, /* @__PURE__ */ React.createElement("h2", { className: "run-title" }, "\u65B0\u5EFA\u8FD0\u884C"), /* @__PURE__ */ React.createElement("div", { className: "nr-sub" }, "\u4E0A\u4F20\u77ED\u5267\u7D20\u6750\uFF0C\u542F\u52A8\u751F\u4EA7\u6D41\u6C34\u7EBF \xB7 New producer run")), /* @__PURE__ */ React.createElement("div", { className: "nr-card" }, /* @__PURE__ */ React.createElement("div", { className: "nr-card-title" }, "\u5267\u76EE Drama"), /* @__PURE__ */ React.createElement("div", { className: "nr-fields" }, /* @__PURE__ */ React.createElement("label", { className: "field" }, /* @__PURE__ */ React.createElement("span", { className: "field-k" }, "\u5267\u76EE\u540D\u79F0"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "field-in",
        placeholder: "\u5982\uFF1A\u8352\u5E74\u5168\u6751\u5543\u6811\u76AE\uFF0C\u6211\u6709\u7CFB\u7EDF\u6EE1\u4ED3\u8089",
        value: title,
        onChange: (e) => setTitle(e.target.value)
      }
    )), /* @__PURE__ */ React.createElement("label", { className: "field field-narrow" }, /* @__PURE__ */ React.createElement("span", { className: "field-k" }, "\u5267\u76EE ID"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "field-in mono",
        placeholder: slugify(title) || "drama",
        value: idTouched ? dramaId : dramaId || slugify(title),
        onChange: (e) => {
          setIdTouched(true);
          setDramaId(slugify(e.target.value));
        }
      }
    )))), /* @__PURE__ */ React.createElement("div", { className: "nr-card" }, /* @__PURE__ */ React.createElement("div", { className: "nr-card-title" }, "\u5267\u96C6\u7D20\u6750 Episodes", episodes.length > 0 && /* @__PURE__ */ React.createElement("span", { className: "nr-count" }, episodes.length, " \u96C6")), /* @__PURE__ */ React.createElement(
      "div",
      {
        className: "dropzone" + (drag ? " is-drag" : ""),
        onDragOver: (e) => {
          e.preventDefault();
          setDrag(true);
        },
        onDragLeave: () => setDrag(false),
        onDrop,
        onClick: () => inputRef.current && inputRef.current.click()
      },
      /* @__PURE__ */ React.createElement("div", { className: "dz-ico" }, "\u2913"),
      /* @__PURE__ */ React.createElement("div", { className: "dz-main" }, "\u62D6\u5165 MP4 \u6587\u4EF6\uFF0C\u6216\u70B9\u51FB\u9009\u62E9"),
      /* @__PURE__ */ React.createElement("div", { className: "dz-sub" }, "\u652F\u6301 .mp4 / .mov / .m4v \xB7 \u89C6\u9891\u4EC5\u6682\u5B58\u5728\u672C\u5730\u5236\u4F5C\u73AF\u5883\uFF0C\u4E0D\u5199\u5165 runtime \u5305"),
      /* @__PURE__ */ React.createElement(
        "input",
        {
          ref: inputRef,
          type: "file",
          accept: "video/*,.mp4,.mov,.m4v",
          multiple: true,
          style: { display: "none" },
          onChange: (e) => addFiles(e.target.files)
        }
      )
    ), episodes.length > 0 && /* @__PURE__ */ React.createElement("div", { className: "ep-list" }, renumber(episodes).map((e) => /* @__PURE__ */ React.createElement("div", { className: "ep-row", key: e.key }, /* @__PURE__ */ React.createElement("span", { className: "ep-id mono" }, e.epId), /* @__PURE__ */ React.createElement("span", { className: "ep-name" }, e.name), /* @__PURE__ */ React.createElement("span", { className: "ep-size mono" }, fmtMB(e.size)), /* @__PURE__ */ React.createElement("button", { className: "ep-x", onClick: () => removeEp(e.key), title: "\u79FB\u9664" }, "\u2715"))))), /* @__PURE__ */ React.createElement("div", { className: "nr-card" }, /* @__PURE__ */ React.createElement("div", { className: "nr-card-title" }, "\u6D41\u6C34\u7EBF\u9009\u9879 Pipeline"), /* @__PURE__ */ React.createElement("div", { className: "nr-options" }, /* @__PURE__ */ React.createElement("div", { className: "opt" }, /* @__PURE__ */ React.createElement("span", { className: "field-k" }, "\u56FE\u6A21\u5F0F graph_mode"), /* @__PURE__ */ React.createElement("div", { className: "segmented" }, /* @__PURE__ */ React.createElement("button", { className: "seg" + (mode === "base" ? " is-on" : ""), onClick: () => setMode("base") }, "\u57FA\u7840 base"), /* @__PURE__ */ React.createElement("button", { className: "seg" + (mode === "llm" ? " is-on" : ""), onClick: () => setMode("llm") }, "LLM \u589E\u5F3A")), /* @__PURE__ */ React.createElement("span", { className: "opt-hint" }, mode === "llm" ? "\u786E\u5B9A\u6027\u53EC\u56DE + LLM \u8BED\u4E49\u6316\u6398\u4E0E\u521D\u7B5B\uFF0Cshortlist \u66F4\u8D34\u8FD1\u89C2\u4F17\u60C5\u7EEA\u70B9\u3002" : "\u4EC5\u786E\u5B9A\u6027\u53EC\u56DE\uFF0C\u53EF\u590D\u73B0\u57FA\u7EBF\uFF0C\u4E0D\u8C03\u7528\u4EFB\u4F55 provider\u3002")), /* @__PURE__ */ React.createElement("div", { className: "opt" }, /* @__PURE__ */ React.createElement("span", { className: "field-k" }, "\u5019\u9009\u53EC\u56DE\u9884\u7B97"), /* @__PURE__ */ React.createElement("div", { className: "recall-val mono" }, episodes.length ? recall : "\u2014"), /* @__PURE__ */ React.createElement("span", { className: "opt-hint" }, "\u6309\u7D20\u6750\u6570\u81EA\u52A8\u63A8\u5BFC\uFF08\u7EA6 4\xD7\u96C6\u6570\uFF0C\u9650 20\u2013400\uFF09\u3002")))), /* @__PURE__ */ React.createElement("div", { className: "nr-actions" }, /* @__PURE__ */ React.createElement("span", { className: "nr-note" }, "\u4EBA\u5DE5\u8BC4\u5BA1\u662F\u53D1\u5E03\u524D\u7684\u5FC5\u7ECF\u95F8\u95E8\u2014\u2014\u542F\u52A8\u540E\u6D41\u6C34\u7EBF\u4F1A\u505C\u5728\u8BC4\u5BA1\u95F8\u95E8\u7B49\u5F85\u4F60\u786E\u8BA4\u3002"), /* @__PURE__ */ React.createElement("button", { className: "btn btn-primary btn-lg", disabled: !canStart, onClick: start }, busy ? "\u542F\u52A8\u4E2D\u2026" : "\u5F00\u59CB\u8FD0\u884C \u2192")));
  }
  window.Studio = Object.assign(window.Studio || {}, { NewRun });
})();
