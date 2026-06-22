// Async feature bundle for LazyMotion (Phase 11.6).
// Importing this lazily keeps framer-motion's DOM features out of the initial
// chunk — only the tiny `m` stub ships up front (bundle budget).
// `domMax` = domAnimation + drag + layout projection. 11.6 needs drag
// (velocity-dismiss, KMP-001) and layout (LayoutGroup/layoutId, KMP-003), so we
// upgrade from domAnimation. It stays code-split off the entry chunk.
export { domMax as default } from "framer-motion";
