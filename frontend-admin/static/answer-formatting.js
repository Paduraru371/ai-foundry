/* Safe, dependency-free rendering for the two structured answer formats. */
(function () {
  "use strict";

  function stripFence(text) {
    const value = String(text || "").trim();
    const match = value.match(/^```(?:markdown|md)?\s*\n([\s\S]*?)\n```$/i);
    return match ? match[1].trim() : value;
  }

  function paragraph(text) {
    const node = document.createElement("p");
    node.textContent = text;
    return node;
  }

  function renderBulletList(container, text) {
    const lines = stripFence(text).split(/\r?\n/);
    let list = null;
    let listType = "";
    let lastPrimary = null;
    let nested = null;
    let nestedType = "";

    lines.forEach((raw) => {
      const match = raw.match(/^(\s*)([-*•]|\d+[.)])\s+(.+)$/);
      if (!match) {
        const value = raw.trim();
        if (value) container.append(paragraph(value));
        list = null;
        listType = "";
        lastPrimary = null;
        nested = null;
        return;
      }
      const type = /^\d/.test(match[2]) ? "ol" : "ul";
      const isNested = match[1].replace(/\t/g, "  ").length >= 2;
      const item = document.createElement("li");
      item.textContent = match[3].trim();

      if (isNested && lastPrimary) {
        if (!nested || nestedType !== type) {
          nested = document.createElement(type);
          nested.className = "answer-sublist";
          lastPrimary.append(nested);
          nestedType = type;
        }
        nested.append(item);
        return;
      }
      if (!list || listType !== type) {
        list = document.createElement(type);
        list.className = "answer-list";
        container.append(list);
        listType = type;
      }
      list.append(item);
      lastPrimary = item;
      nested = null;
      nestedType = "";
    });
  }

  function splitRow(line) {
    let value = line.trim();
    if (value.startsWith("|")) value = value.slice(1);
    if (value.endsWith("|")) value = value.slice(0, -1);
    const cells = [];
    let cell = "";
    let escaped = false;
    for (const character of value) {
      if (escaped) {
        cell += character;
        escaped = false;
      } else if (character === "\\") {
        escaped = true;
      } else if (character === "|") {
        cells.push(cell.trim());
        cell = "";
      } else {
        cell += character;
      }
    }
    if (escaped) cell += "\\";
    cells.push(cell.trim());
    return cells;
  }

  function separatorAlignment(value) {
    const clean = value.trim();
    if (!/^:?-{3,}:?$/.test(clean)) return null;
    if (clean.startsWith(":") && clean.endsWith(":")) return "center";
    if (clean.endsWith(":")) return "right";
    return "left";
  }

  function normalizeRow(cells, width) {
    const result = cells.slice(0, width);
    if (cells.length > width && width) {
      result[width - 1] = cells.slice(width - 1).join(" | ");
    }
    while (result.length < width) result.push("");
    return result;
  }

  function renderTable(container, text) {
    const lines = stripFence(text).split(/\r?\n/);
    const separatorIndex = lines.findIndex((line, index) => {
      if (index === 0 || !line.includes("|")) return false;
      const cells = splitRow(line);
      return cells.length > 1 && cells.every((cell) => separatorAlignment(cell));
    });
    if (separatorIndex < 1) return false;

    const headers = splitRow(lines[separatorIndex - 1]);
    const alignments = splitRow(lines[separatorIndex]).map(separatorAlignment);
    if (headers.length < 2 || headers.length !== alignments.length) return false;

    lines.slice(0, separatorIndex - 1).map((line) => line.trim())
      .filter(Boolean).forEach((line) => container.append(paragraph(line)));

    const wrapper = document.createElement("div");
    wrapper.className = "answer-table-wrap";
    wrapper.tabIndex = 0;
    const table = document.createElement("table");
    table.className = "answer-table";
    const head = document.createElement("thead");
    const headRow = document.createElement("tr");
    headers.forEach((value, index) => {
      const cell = document.createElement("th");
      cell.scope = "col";
      cell.textContent = value;
      cell.className = `align-${alignments[index]}`;
      headRow.append(cell);
    });
    head.append(headRow);
    table.append(head);

    const body = document.createElement("tbody");
    let end = separatorIndex + 1;
    for (; end < lines.length && lines[end].includes("|"); end += 1) {
      const row = document.createElement("tr");
      normalizeRow(splitRow(lines[end]), headers.length).forEach((value, index) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        cell.className = `align-${alignments[index]}`;
        row.append(cell);
      });
      body.append(row);
    }
    table.append(body);
    wrapper.append(table);
    container.append(wrapper);
    lines.slice(end).map((line) => line.trim()).filter(Boolean)
      .forEach((line) => container.append(paragraph(line)));
    return true;
  }

  function render(container, text, format) {
    container.replaceChildren();
    container.classList.remove("formatted-bullets", "formatted-table");
    if (format === "bullet_list") {
      container.classList.add("formatted-bullets");
      renderBulletList(container, text);
    } else if (format === "table" && renderTable(container, text)) {
      container.classList.add("formatted-table");
    } else {
      container.textContent = text || "";
    }
  }

  window.AnswerFormatting = { render };
})();
