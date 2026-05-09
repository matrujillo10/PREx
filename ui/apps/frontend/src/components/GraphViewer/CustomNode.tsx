import React from "react";
import { Handle, Position } from "@xyflow/react";
import { GraphNodePayload } from "../../config/graphConfigSchema";

export function CustomNode({ data }: { data: { payload: GraphNodePayload; _style: any; _kindStyle: any } }) {
  const { payload, _style, _kindStyle } = data;
  
  const borderColor = _style?.borderColor || "border-gray-300";
  const bg = _style?.backgroundColor || "bg-white";
  const text = _style?.textColor || "text-gray-700";
  const shape = _kindStyle?.shape || "rounded-md";

  return (
    <div className={`px-4 py-3 shadow-sm border-2 ${shape} ${borderColor} ${bg}`}>
      <Handle type="target" position={Position.Top} className="w-16 !bg-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
      
      <div className="flex flex-col min-w-[120px]">
        <div className="flex items-center justify-between gap-2 mb-1">
          <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">
            {payload.kind}
          </span>
          {payload.change_state !== "unchanged" && (
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${borderColor} ${text}`}>
              {payload.change_state}
            </span>
          )}
        </div>
        
        {/* Discriminator based label selection */}
        <div className={`font-semibold text-sm ${text}`}>
          {'name' in payload ? payload.name : ('path' in payload ? payload.path.split('/').pop() : 'Hunk')}
        </div>

        {/* Patch preview for hunch */}
        {payload.kind === 'hunk' && (
           <pre className="text-[9px] mt-2 overflow-x-hidden text-gray-600 bg-black/5 p-1 rounded">
             {payload.patch.split("\n")[0]}...
           </pre>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="w-16 !bg-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
    </div>
  );
}
