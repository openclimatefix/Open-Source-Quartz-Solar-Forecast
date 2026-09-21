"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";

const formSchema = z.object({
  latitude: z.coerce
    .number({ required_error: "Site latitude is required." })
    .min(-90, {
      message: "Latitude must be greater than or equal to -90.",
    })
    .max(90, {
      message: "Latitude must be smaller than or equal to 90",
    }),
  longitude: z.coerce
    .number({ required_error: "Site longitude is required." })

    .min(-180, {
      message: "Longitude  must be greater than or equal to -180",
    })
    .max(180, {
      message: "Longitude must be smaller than or equal to 180",
    }),
  capacity_kwp: z.coerce
    .number({ required_error: "Site capacity is required." })
    .gt(0, { message: "Site capacity must be greather than 0." }),
});

export function PVForecastForm({ updatePredictions }) {
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    mode: "onChange",
    defaultValues: {
      latitude: 51.75,
      longitude: -1.25,
      capacity_kwp: 1.25,
    },
  });

  async function onSubmit(values: z.infer<typeof formSchema>) {
    const response = await fetch(`http://localhost:8000/forecast/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ site: values }),
    });
    const data = await response.json();
    updatePredictions(data.predictions.power_kw);
  }
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormField
          control={form.control}
          name="latitude"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Latitude</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormDescription>The latitude of the site.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="longitude"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Longitude</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormDescription>The longitude of the site.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="capacity_kwp"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Capacity</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormDescription>The capacity (kwp) of the site.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit">Predict</Button>
      </form>
    </Form>
  );
}
