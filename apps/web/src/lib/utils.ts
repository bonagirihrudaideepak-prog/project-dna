export const cn2 = (...classes: Array<string | false | null | undefined>) =>
  classes.filter((c) => c !== undefined && c !== null && c !== false && c !== "").join(" ");
