declare function renderMathInElement(
  element: HTMLElement,
  options?: {
    delimiters?: { left: string; right: string; display: boolean }[];
    throwOnError?: boolean;
    trust?: boolean;
  },
): void;

export default renderMathInElement;
