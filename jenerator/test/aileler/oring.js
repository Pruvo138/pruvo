function oring(p) {
  var merkezYaricap = p.ic_cap / 2 + p.kesit_cap / 2;
  var kesitAlani;

  if (p.profil === "kare") {
    kesitAlani = p.kesit_cap * p.kesit_cap;
  } else if (p.profil === "pahli") {
    kesitAlani = 0.875 * p.kesit_cap * p.kesit_cap;
  } else {
    kesitAlani = Math.PI * p.kesit_cap * p.kesit_cap / 4;
  }

  return kesitAlani * 2 * Math.PI * merkezYaricap;
}
