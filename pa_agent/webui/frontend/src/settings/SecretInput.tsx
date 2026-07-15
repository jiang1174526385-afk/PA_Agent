import { useState } from "react";

/** Secret field: shows the masked value as a placeholder and never re-echoes
 * the real value. Requires an explicit "修改" click before typing is enabled,
 * so a settings-form re-render can't silently blank out a stored secret.
 * Returns `undefined` (unchanged) unless the user opted in to edit. */
export function SecretInput({
  label,
  maskedValue,
  isSet,
  value,
  onChange,
}: {
  label: string;
  maskedValue: string;
  isSet: boolean;
  value: string | undefined;
  onChange: (value: string | undefined) => void;
}) {
  const [editing, setEditing] = useState(false);
  const inputId = `secret-${label.replace(/\s+/g, "-").toLowerCase()}`;

  return (
    <div className="form-row">
      <label htmlFor={inputId}>{label}</label>
      {editing ? (
        <input
          id={inputId}
          type="password"
          autoFocus
          value={value ?? ""}
          placeholder="输入新值，留空则清空"
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            id={inputId}
            type="password"
            value={maskedValue}
            disabled
            placeholder={isSet ? "" : "未设置"}
          />
          <button
            type="button"
            onClick={() => {
              setEditing(true);
              onChange("");
            }}
          >
            修改
          </button>
        </div>
      )}
    </div>
  );
}
