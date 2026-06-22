// Async feature bundle for LazyMotion (Phase 11.5).
// Importing this lazily keeps framer-motion's ~17KB DOM-animation features out
// of the initial chunk — only the tiny `m` stub ships up front (bundle budget).
// `domAnimation` = animations + variants + exit, no drag/layout (YAGNI for now).
export { domAnimation as default } from "framer-motion";
