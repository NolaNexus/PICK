import * as React from 'react'
import { cn } from '@/lib/utils'

type TableProps = React.HTMLAttributes<HTMLTableElement>
export function Table({ className, ...props }: TableProps) {
  return <div className={cn('w-full overflow-auto', className)} {...props} />
}

type TableHeaderProps = React.HTMLAttributes<HTMLTableSectionElement>
export function TableHeader({ className, ...props }: TableHeaderProps) {
  return <thead className={cn('border-b', className)} {...props} />
}

type TableBodyProps = React.HTMLAttributes<HTMLTableSectionElement>
export function TableBody({ className, ...props }: TableBodyProps) {
  return <tbody className={cn('[&_tr]:last:border-b-0', className)} {...props} />
}

type TableFooterProps = React.HTMLAttributes<HTMLTableSectionElement>
export function TableFooter({ className, ...props }: TableFooterProps) {
  return <tfoot className={cn('border-t font-medium bg-muted/50', className)} {...props} />
}

type TableRowProps = React.HTMLAttributes<HTMLTableRowElement>
export function TableRow({ className, ...props }: TableRowProps) {
  return <tr className={cn('border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted', className)} {...props} />
}

type TableHeadProps = React.HTMLAttributes<HTMLTableCellElement>
export function TableHead({ className, ...props }: TableHeadProps) {
  return (
    <th
      className={cn(
        'h-10 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0',
        className
      )}
      {...props}
    />
  )
}

type TableCellProps = React.HTMLAttributes<HTMLTableDataCellElement> & {
  colSpan?: number
}
export function TableCell({ className, ...props }: TableCellProps) {
  return (
    <td className={cn('p-4 align-middle [&:has([role=checkbox])]:pl-0', className)} {...props} />
  )
}

type TableCaptionProps = React.HTMLAttributes<HTMLTableCaptionElement>
export function TableCaption({ className, ...props }: TableCaptionProps) {
  return <caption className={cn('text-foreground text-sm', className)} {...props} />
}
