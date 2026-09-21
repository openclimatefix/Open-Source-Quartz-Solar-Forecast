import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type PredictionsType = Record<string, number>;

export function PredictionTable({ predictions }: { predictions: PredictionsType }) {
  return (
    <Table className="border">
      <TableCaption>
        Solar energy predicted for each time step in a 15 minute interval from
        now
      </TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead className="w-[200px]">Datetime</TableHead>
          <TableHead className="text-right">Power (kw)</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {Object.keys(predictions).map((datetime) => (
          <TableRow key={datetime}>
            <TableCell>{datetime}</TableCell>
            <TableCell className="text-right">
              {predictions[datetime].toFixed(6)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
