import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Workbench } from "./Workbench";

describe("Workbench", () => {
  it("labels the secondary coaching region", () => {
    render(<Workbench primary={<p>主训练区</p>} aside={<p>辅助信息</p>} asideLabel="训练教练" />);

    expect(screen.getByText("主训练区")).toBeVisible();
    expect(screen.getByRole("complementary", { name: "训练教练" })).toHaveTextContent("辅助信息");
  });
});
