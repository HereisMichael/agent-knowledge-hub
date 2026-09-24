import { useLayoutEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import renderMathInElement from "../../vendor/katex/contrib/auto-render.mjs";


const mathOptions = {
  delimiters: [
    { left: "$$", right: "$$", display: true },
    { left: "$", right: "$", display: false },
    { left: "\\[", right: "\\]", display: true },
    { left: "\\(", right: "\\)", display: false },
  ],
  throwOnError: false,
  trust: false,
};

function useMathRendering<T extends HTMLElement>(value: string) {
  const ref = useRef<T>(null);
  useLayoutEffect(() => {
    if (ref.current) renderMathInElement(ref.current, mathOptions);
  }, [value]);
  return ref;
}

export function MathMarkdown({ markdown, className }: { markdown: string; className?: string }) {
  const ref = useMathRendering<HTMLDivElement>(markdown);
  return <div key={markdown} ref={ref} className={className}><ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>{markdown}</ReactMarkdown></div>;
}

export function MathTitle({ text }: { text: string }) {
  const ref = useMathRendering<HTMLHeadingElement>(text);
  return <h2 key={text} ref={ref}>{text}</h2>;
}

export function MathInline({ text, className }: { text: string; className?: string }) {
  const ref = useMathRendering<HTMLSpanElement>(text);
  return <span key={text} ref={ref} className={className}>{text}</span>;
}
