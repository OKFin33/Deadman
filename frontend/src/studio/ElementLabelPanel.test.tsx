import { render, screen, fireEvent } from "@testing-library/react";
import { useState } from "react";
import { ElementLabelPanel } from "./ElementLabelPanel";
import type { MomentLabel } from "./reviewApi";

// Harness mirrors how StudioReview owns the label state, so we can assert the onChange-driven shape.
function Harness() {
  const [value, setValue] = useState<MomentLabel>({});
  return (
    <div>
      <div data-testid="json">{JSON.stringify(value)}</div>
      <ElementLabelPanel
        lead="听完心里怪不是滋味的"
        candidates={[
          { display_text: "长辈的惦记最戳人", selected_echo: "可不是" },
          { display_text: "太耗人了", selected_echo: "确实" },
          { display_text: "感觉复杂", selected_echo: "嗯" },
        ]}
        value={value}
        onChange={setValue}
      />
    </div>
  );
}

function state() {
  return JSON.parse(screen.getByTestId("json").textContent || "{}");
}

describe("ElementLabelPanel", () => {
  it("records window-selection and a per-element verdict", () => {
    render(<Harness />);
    fireEvent.click(screen.getByText("会想说")); // window-selection (exact match, not 不会想说)
    fireEvent.click(screen.getAllByText("达标")[0]); // first 达标 = lead row
    expect(state().window).toBe("accept");
    expect(state().lead.v).toBe("ok");
  });

  it("flagging 不达标 reveals the sub-pattern picker", () => {
    render(<Harness />);
    // 7 rows in DOM order: lead, say1, echo1, say2, echo2, say3, echo3
    fireEvent.click(screen.getAllByText("不达标")[2]); // echo1
    expect(state().echoes[0].v).toBe("bad");
    expect(screen.getByText("选细分模式…")).toBeInTheDocument();
  });

  it("「本卡全达标」 marks lead + all says + all echoes ok", () => {
    render(<Harness />);
    fireEvent.click(screen.getByText("✓ 本卡全达标"));
    const s = state();
    expect(s.lead.v).toBe("ok");
    expect(s.says.every((x: { v?: string }) => x.v === "ok")).toBe(true);
    expect(s.echoes.every((x: { v?: string }) => x.v === "ok")).toBe(true);
    expect(s.says).toHaveLength(3);
  });
});
