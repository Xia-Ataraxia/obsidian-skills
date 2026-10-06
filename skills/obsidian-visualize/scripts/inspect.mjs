#!/usr/bin/env node
// Adapted from Jonghak Seo pi-extension; see ../NOTICE and ../PROVENANCE.md.
// Read-only inspection and layout lint. No server, browser, or writer.
import fs from "node:fs";
import path from "node:path";
const die = (message) => { console.error(message); process.exit(1); };
function loadScene(file) {
 try {
  let content = fs.readFileSync(file, "utf8");
  if (file.endsWith(".md")) {
   const heading = content.lastIndexOf("\n## Drawing\n");
   if (heading < 0) throw new Error("missing Drawing section");
   const tail = content.slice(heading);
   if (tail.includes("```compressed-json")) throw new Error("compressed-json requires plugin scene readback; never hand-patch it");
   const match = tail.match(/```json\n([\s\S]*?)\n```/);
   if (!match) throw new Error("missing plain JSON drawing fence");
   content = match[1];
  } else if (!file.endsWith(".excalidraw")) throw new Error("expected .excalidraw.md or .excalidraw");
  const data = JSON.parse(content);
  if (!data || data.type !== "excalidraw" || !Array.isArray(data.elements)) throw new Error("invalid scene envelope");
  for (const e of data.elements) {
   if (!e || typeof e !== "object" || Array.isArray(e) || typeof e.type !== "string") throw new Error("invalid element");
   for (const key of ["x", "y", "width", "height", "fontSize"])
    if (key in e && (typeof e[key] !== "number" || !Number.isFinite(e[key]) || (["width", "height", "fontSize"].includes(key) && e[key] < 0))) throw new Error("invalid geometry: " + key);
   for (const key of ["boundElements", "groupIds", "points"]) if (key in e && e[key] !== null && !Array.isArray(e[key])) throw new Error("invalid " + key);
   for (const binding of e.boundElements || []) if (!binding || typeof binding.id !== "string") throw new Error("invalid bound element");
   for (const point of e.points || []) if (!Array.isArray(point) || point.length !== 2 || !point.every(v => typeof v === "number" && Number.isFinite(v))) throw new Error("invalid point");
   for (const key of ["start", "end", "startBinding", "endBinding"]) if (e[key] !== undefined && e[key] !== null && (typeof e[key] !== "object" || Array.isArray(e[key]))) throw new Error("invalid binding");
   if (typeof e.version === "number" && !["x", "y", "width", "height"].every(key => typeof e[key] === "number")) throw new Error("full elements require geometry");
  }
  return {data, elements: data.elements.filter(e => !e.isDeleted)};
 } catch (err) { return {error: err.message}; }
}

const isSkel = (e) => typeof e.version !== "number";
const SHAPES = new Set(["rectangle", "ellipse", "diamond"]);
const LINEAR = new Set(["arrow", "line"]);
const round = (n) => (typeof n === "number" ? Math.round(n) : "?");

function textWidthEstimate(text, fontSize = 20) {
	let max = 0;
	for (const line of String(text).split("\n")) {
		let w = 0;
		for (const ch of line)
			w += /[\u1100-\u11ff\u3000-\u9fff\uac00-\ud7af\uff00-\uffef]/.test(ch) ? fontSize : fontSize * 0.55;
		max = Math.max(max, w);
	}
	return max;
}

function labelOf(el, byId) {
	if (el.label?.text) return el.label.text;
	if (el.type === "text") return el.text;
	const bound = (el.boundElements || []).find((b) => b.type === "text");
	return bound ? byId.get(bound.id)?.text : undefined;
}

function arrowEnds(el) {
	const s = el.start?.id ?? el.startBinding?.elementId;
	const e = el.end?.id ?? el.endBinding?.elementId;
	return [s, e];
}

function inspect(file) {
	const { error, elements } = loadScene(file);
	if (error) die(error);
	const byId = new Map(elements.map((e) => [e.id, e]));
	const visible = elements.filter((e) => !(e.type === "text" && e.containerId));
	const count = (pred) => visible.filter(pred).length;
	const boxes = visible.filter((e) => typeof e.x === "number" && typeof e.width === "number");
	const minX = Math.min(...boxes.map((e) => e.x));
	const minY = Math.min(...boxes.map((e) => e.y));
	const maxX = Math.max(...boxes.map((e) => e.x + Math.abs(e.width)));
	const maxY = Math.max(...boxes.map((e) => e.y + Math.abs(e.height ?? 0)));
	console.log(
		`${path.basename(file)}  요소 ${visible.length}개 (도형 ${count((e) => SHAPES.has(e.type))}, 화살표/선 ${count((e) => LINEAR.has(e.type))}, 텍스트 ${count((e) => e.type === "text")})` +
			(boxes.length ? `  범위 x ${round(minX)}~${round(maxX)}, y ${round(minY)}~${round(maxY)}` : "") +
			(elements.some(isSkel) ? "  [스켈레톤 포함: 플러그인에서 정규화 필요]" : ""),
	);
	for (const el of visible) {
		const label = labelOf(el, byId);
		const lbl = label ? `  "${label.replace(/\n/g, "\\n")}"` : "";
		const style = [
			el.backgroundColor && el.backgroundColor !== "transparent" ? `bg=${el.backgroundColor}` : "",
			el.strokeColor && el.strokeColor !== "#1e1e1e" ? `stroke=${el.strokeColor}` : "",
		]
			.filter(Boolean)
			.join(" ");
		if (LINEAR.has(el.type)) {
			const [s, e] = arrowEnds(el);
			console.log(
				`[${el.type}] ${el.id}  ${s ?? "·"} → ${e ?? "·"}${lbl}  @(${round(el.x)},${round(el.y)})${style ? "  " + style : ""}`,
			);
		} else {
			console.log(
				`[${el.type}] ${el.id}  @(${round(el.x)},${round(el.y)} ${round(el.width)}×${round(el.height)})${lbl}${style ? "  " + style : ""}${el.frameId ? `  frame=${el.frameId}` : ""}`,
			);
		}
	}
}

function lint(file) {
	const { error, data, elements } = loadScene(file);
	const errors = [];
	const warns = [];
	if (error) errors.push(error);
	else {
		if (data.type !== "excalidraw") errors.push(`최상위 type이 "excalidraw"가 아닙니다: ${data.type}`);
		if (!Array.isArray(data.elements)) errors.push("최상위 elements 배열이 없습니다");
		const all = Array.isArray(data.elements) ? data.elements : [];
		const ids = new Map();
		for (const e of all) {
			if (!e.type) errors.push(`type 없는 요소: ${JSON.stringify(e).slice(0, 80)}`);
			if (typeof e.id !== "string" || !e.id) {
				if (isSkel(e) && !LINEAR.has(e.type)) warns.push(`id 없는 ${e.type} 요소 (나중에 수정·연결하려면 id 권장)`);
				if (!isSkel(e)) errors.push("id 없는 정식 요소");
				continue;
			}
			if (ids.has(e.id)) errors.push(`중복 id: ${e.id}`);
			ids.set(e.id, e);
		}
		const ref = (owner, id, what) => {
			if (id && !ids.has(id)) errors.push(`${owner.id ?? owner.type}의 ${what}가 없는 요소를 가리킴: ${id}`);
		};
		for (const e of elements) {
			ref(e, e.containerId, "containerId");
			ref(e, e.frameId, "frameId");
			for (const b of e.boundElements || []) ref(e, b.id, "boundElements");
			ref(e, e.startBinding?.elementId, "startBinding");
			ref(e, e.endBinding?.elementId, "endBinding");
			ref(e, e.start?.id, "start.id");
			ref(e, e.end?.id, "end.id");
			if (!isSkel(e)) {
				for (const binding of [e.startBinding, e.endBinding]) {
					const target = ids.get(binding?.elementId);
					if (target && !(target.boundElements || []).some(b => b.id === e.id && b.type === "arrow"))
						errors.push(`${e.id}: arrow binding is not mirrored`);
				}
				const container = ids.get(e.containerId);
				if (container && !(container.boundElements || []).some(b => b.id === e.id && b.type === "text"))
					errors.push(`${e.id}: text binding is not mirrored`);
			}
			if (isSkel(e) && LINEAR.has(e.type)) {
				const [s, t] = arrowEnds(e);
				if (typeof e.x !== "number" && !(s && t))
					errors.push(`${e.id ?? "arrow"}: x/y도 없고 start.id·end.id도 없습니다`);
				if (typeof e.x !== "number" && s && t) {
					for (const id of [s, t]) {
						const target = ids.get(id);
						if (target && (typeof target.width !== "number" || typeof target.height !== "number"))
							errors.push(`${e.id ?? "arrow"}: 자동 연결 대상 ${id}에 width/height가 없습니다`);
					}
				}
			}
			if (isSkel(e) && SHAPES.has(e.type) && e.label?.text && typeof e.width === "number") {
				// Fonts render wider than the estimate; diamonds need extra room around their text.
				const fontSize = e.label.fontSize ?? 20;
				const scale = e.type === "diamond" ? 1.5 : 1;
				const needW = (textWidthEstimate(e.label.text, fontSize) + 48) * scale;
				const needH = (fontSize * 1.25 * e.label.text.split("\n").length + 32) * scale;
				if (needW > e.width || (typeof e.height === "number" && needH > e.height))
					warns.push(
						`${e.id}: 라벨 "${e.label.text.split("\n")[0]}"이 ${e.width}×${e.height}에 빠듯해 보임 (약 ${Math.round(needW)}×${Math.round(needH)}px 필요)`,
					);
			}
		}
		// partial overlaps between top-level boxes (containment is treated as intentional grouping)
		const boxes = elements
			.filter((e) => (SHAPES.has(e.type) || (e.type === "text" && !e.containerId)) && typeof e.x === "number")
			.map((e) => {
				const w =
					typeof e.width === "number"
						? e.width
						: e.type === "text"
							? textWidthEstimate(e.text, e.fontSize ?? 20)
							: undefined;
				const h =
					typeof e.height === "number"
						? e.height
						: e.type === "text"
							? (e.fontSize ?? 20) * 1.25 * String(e.text).split("\n").length
							: undefined;
				return w === undefined || h === undefined
					? null
					: { id: e.id ?? e.type, x1: e.x, y1: e.y, x2: e.x + w, y2: e.y + h };
			})
			.filter(Boolean);
		const contains = (a, b) => a.x1 <= b.x1 && a.y1 <= b.y1 && a.x2 >= b.x2 && a.y2 >= b.y2;
		for (let i = 0; i < boxes.length; i++)
			for (let j = i + 1; j < boxes.length; j++) {
				const a = boxes[i];
				const b = boxes[j];
				const ix = Math.min(a.x2, b.x2) - Math.max(a.x1, b.x1);
				const iy = Math.min(a.y2, b.y2) - Math.max(a.y1, b.y1);
				if (ix > 2 && iy > 2 && !contains(a, b) && !contains(b, a))
					warns.push(`겹침: ${a.id} ↔ ${b.id} (${Math.round(ix)}×${Math.round(iy)})`);
			}
		for (const e of elements) {
			if (e.type !== "arrow") continue;
			const [s, t] = arrowEnds(e);
			if (!s || !t) warns.push(`${e.id ?? "arrow"}: 한쪽 이상이 도형에 연결되지 않은 화살표`);
		}
	}
	for (const m of errors) console.log(`ERROR ${m}`);
	for (const m of warns) console.log(`WARN  ${m}`);
	console.log(errors.length || warns.length ? `오류 ${errors.length}, 경고 ${warns.length}` : "OK");
	process.exit(errors.length ? 1 : 0);
}


const [command, file, ...extra] = process.argv.slice(2);
if (!file || extra.length || !["inspect", "lint"].includes(command)) die("usage: inspect.mjs inspect|lint <drawing.excalidraw.md|scene.excalidraw>");
if (command === "inspect") inspect(path.resolve(file));
else lint(path.resolve(file));
