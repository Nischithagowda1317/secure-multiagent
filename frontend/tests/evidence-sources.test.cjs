const assert = require("node:assert/strict");
const fs = require("node:fs");
const { test } = require("node:test");
const ts = require("typescript");
const { createElement } = require("react");
const { renderToStaticMarkup } = require("react-dom/server");

// Compile the real TSX component for Node's test runner without adding a
// separate browser/test dependency. Its type-only imports are erased.
const previousLoader = require.extensions[".tsx"];
require.extensions[".tsx"] = (module, filename) => {
  const result = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
    fileName: filename,
  });
  module._compile(result.outputText, filename);
};
const EvidenceSources = require("../src/components/EvidenceSources.tsx").default;
if (previousLoader) require.extensions[".tsx"] = previousLoader;
else delete require.extensions[".tsx"];

function source(score, title = "Policy evidence") {
  return { source_id: "DOC001", title, source_type: "Document", section: null, score };
}

test("a chat answer renders alongside sources with null and missing scores", () => {
  const html = renderToStaticMarkup(createElement("section", null,
    createElement("p", null, "The chatbot answer remains visible."),
    createElement(EvidenceSources, { sources: [source(null), source(undefined, "Database evidence")] }),
  ));
  assert.match(html, /The chatbot answer remains visible/);
  assert.match(html, /Policy evidence/);
  assert.match(html, /Database evidence/);
  assert.doesNotMatch(html, /Similarity/);
});

test("zero and finite scores remain visible with three decimal places", () => {
  const html = renderToStaticMarkup(createElement(EvidenceSources, {
    sources: [source(null), source(0), source(0.81234)],
  }));
  assert.match(html, /Similarity 0\.000/);
  assert.match(html, /Similarity 0\.812/);
  assert.equal((html.match(/Similarity/g) || []).length, 2);
});

test("non-finite scores do not render invalid similarity values", () => {
  const html = renderToStaticMarkup(createElement(EvidenceSources, {
    sources: [source(NaN), source(Infinity)],
  }));
  assert.doesNotMatch(html, /Similarity|NaN|Infinity/);
});
