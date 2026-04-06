import ScarcityBadge from "./ScarcityBadge";

const POTENTIAL_LABELS: Record<number, string> = {
  0: "",
  1: "Rare",
  2: "Epic",
  3: "Unique",
  4: "Legendary",
  5: "Special",
  6: "Mythic",
};

interface UnderpricedItem {
  token_id: string;
  name: string;
  current_price: number;
  fair_value: number;
  discount_pct: number;
  scarcity_score: number;
  starforce?: number;
  potential_grade?: number;
  potential_label?: string;
  category_label?: string;
  listed_at?: string;
  image_url?: string;
}

export default function UnderpricedTable({
  items,
}: {
  items: UnderpricedItem[];
}) {
  if (!items?.length) {
    return (
      <div className="p-8 text-center text-terminal-muted font-mono text-sm">
        Scanning marketplace for underpriced items...
      </div>
    );
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>ITEM</th>
          <th>DETAIL</th>
          <th>PRICE</th>
          <th>FAIR VALUE</th>
          <th>DISCOUNT</th>
          <th>RARITY</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item, index) => (
          <tr key={`${item.token_id}-${index}`}>
            <td className="text-terminal-text font-medium max-w-[150px] truncate">
              {item.name}
            </td>
            <td className="text-terminal-muted text-[10px]">
              {item.starforce && item.starforce > 0
                ? `SF${item.starforce} `
                : ""}
              {item.potential_label || POTENTIAL_LABELS[item.potential_grade || 0] || ""}
            </td>
            <td className="text-terminal-accent tabular-nums">
              {item.current_price.toLocaleString()}
            </td>
            <td className="text-terminal-muted tabular-nums">
              {item.fair_value.toLocaleString()}
            </td>
            <td>
              <span className="text-terminal-green font-bold">
                -{item.discount_pct.toFixed(0)}%
              </span>
            </td>
            <td>
              <ScarcityBadge score={item.scarcity_score} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
