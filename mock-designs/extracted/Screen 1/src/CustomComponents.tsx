import type { ReactNode } from "react";

export const FallbackComponent = (props: object) => {
  return <div {...props} />;
};

export function TextComponent({
  children,
}: {
  children: ReactNode[];
  className?: string;
}) {
  return children;
}

export function ImageComponent(props: object) {
  return <img {...props} />;
}
