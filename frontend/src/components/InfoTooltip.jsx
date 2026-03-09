import { HelpCircle } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';

const InfoTooltip = ({ text, size = 14, className = '' }) => {
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            className={`inline-flex items-center justify-center text-gray-500 hover:text-gray-300 transition-colors focus:outline-none ${className}`}
            onClick={(e) => e.preventDefault()}
          >
            <HelpCircle style={{ width: size, height: size }} />
          </button>
        </TooltipTrigger>
        <TooltipContent
          side="top"
          className="max-w-[260px] bg-gray-800 text-gray-200 text-xs leading-relaxed px-3 py-2 rounded-lg border border-gray-700 shadow-xl z-[100]"
        >
          {text}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

export default InfoTooltip;
