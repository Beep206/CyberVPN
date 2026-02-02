import { ComponentType, SVGProps } from 'react';
import * as Flags3x2 from 'country-flag-icons/react/3x2';

// Cast to ensure type safety when indexing
const Flags = Flags3x2 as Record<string, ComponentType<SVGProps<SVGSVGElement>>>;

interface CountryFlagProps extends SVGProps<SVGSVGElement> {
    code: string;
}

export function CountryFlag({ code, className, ...props }: CountryFlagProps) {
    const FlagComponent = Flags[code.toUpperCase()];

    if (!FlagComponent) {
        return (
            <div
                className={`flex items-center justify-center bg-muted text-[10px] font-mono text-muted-foreground ${className}`}
                title={code}
            >
                {code}
            </div>
        );
    }

    return <FlagComponent className={className} {...props} />;
}
