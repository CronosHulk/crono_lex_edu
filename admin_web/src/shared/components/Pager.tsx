import { TablePagination } from "@mui/material";

export type PagerProps = {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
};

export function Pager({ page, pageSize, total, onPageChange, onPageSizeChange }: PagerProps) {
  return (
    <TablePagination
      component="div"
      count={total}
      page={Math.max(page - 1, 0)}
      rowsPerPage={pageSize}
      rowsPerPageOptions={[50, 100]}
      labelRowsPerPage="На сторінці:"
      labelDisplayedRows={({ from, to, count }) => `${from}-${to} / ${count}`}
      onPageChange={(_, nextPage) => onPageChange(nextPage + 1)}
      onRowsPerPageChange={(event) => onPageSizeChange(Number(event.target.value))}
      sx={{
        borderTop: 1,
        borderColor: "divider",
        color: "text.primary",
        "& .MuiTablePagination-toolbar": {
          minHeight: 64,
          justifyContent: "flex-end",
        },
      }}
    />
  );
}
