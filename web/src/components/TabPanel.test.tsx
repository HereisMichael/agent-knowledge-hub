import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { TabPanel } from "./TabPanel";

function StatefulInput() {
  const [value, setValue] = useState("");
  return <input aria-label="草稿回答" value={value} onChange={(event) => setValue(event.target.value)} />;
}

describe("TabPanel", () => {
  it("preserves mounted page state while hidden", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <TabPanel pageId="quiz" active mounted>
        <StatefulInput />
      </TabPanel>,
    );
    await user.type(screen.getByRole("textbox", { name: "草稿回答" }), "warp specialize");

    rerender(
      <TabPanel pageId="quiz" active={false} mounted>
        <StatefulInput />
      </TabPanel>,
    );
    expect(screen.getByTestId("page-quiz")).not.toBeVisible();

    rerender(
      <TabPanel pageId="quiz" active mounted>
        <StatefulInput />
      </TabPanel>,
    );
    expect(screen.getByRole("textbox", { name: "草稿回答" })).toHaveValue("warp specialize");
  });
});
