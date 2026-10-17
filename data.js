// data.js — the list of dispensers. Edit this file to add, remove or move dispensers.
//
// Coordinates come from your gt-restrooms.csv (Georgia Tech campus map).
// Floors and rooms are PLACEHOLDERS: replace them once you know the real ones.
//
// Fields:
//   id        unique name for the dispenser (we reuse the CSV id)
//   building  what students see
//   floor     floor / room text shown in the popup
//   lat, lng  location on the map
//   fill      starting fill percentage (0-100)
//   demo      true = fake data (shows a "Demo data" badge). Set to false for your real sensor.
//   offline   true = this fake dispenser stops sending readings, so it turns gray (shows the gray pin)

const DISPENSERS = [
  { id: "p264591", building: "Clough Undergraduate Learning Commons", floor: "Floor 1 (placeholder)", lat: 33.774868, lng: -84.3964,   fill: 88,  demo: true },
  { id: "p264520", building: "Gilbert Memorial Library",              floor: "Floor 1 (placeholder)", lat: 33.774426, lng: -84.39579,  fill: 72,  demo: true },
  { id: "p264951", building: "Klaus Advanced Computing Building",     floor: "Floor 1 (placeholder)", lat: 33.777225, lng: -84.39621,  fill: 55,  demo: true },
  { id: "p279898", building: "Stamps Health Services",                floor: "Floor 1 (placeholder)", lat: 33.774773, lng: -84.402885, fill: 40,  demo: true },
  { id: "p473312", building: "Kendeda Building",                      floor: "Floor 2 (placeholder)", lat: 33.778774, lng: -84.399574, fill: 22,  demo: true },
  { id: "p264141", building: "Skiles",                                floor: "Floor 1 (placeholder)", lat: 33.773582, lng: -84.39595,  fill: 12,  demo: true },
  { id: "p279888", building: "Van Leer Building",                     floor: "Floor 1 (placeholder)", lat: 33.775948, lng: -84.397141, fill: 5,   demo: true },
  { id: "p264081", building: "College of Computing",                  floor: "Floor 1 (placeholder)", lat: 33.777363, lng: -84.397354, fill: 0,   demo: true },
  { id: "p264568", building: "Ferst Center for the Arts",             floor: "Floor 1 (placeholder)", lat: 33.775181, lng: -84.399338, fill: 95,  demo: true },
  { id: "p451379", building: "Instructional Center",                  floor: "Floor 1 (placeholder)", lat: 33.775505, lng: -84.401314, fill: 30,  demo: true },
  { id: "p264079", building: "Tech Tower",                            floor: "Floor 1 (placeholder)", lat: 33.772457, lng: -84.39473,  fill: 64,  demo: true, offline: true },
  { id: "p261362", building: "Lyman Hall",                            floor: "Floor 1 (placeholder)", lat: 33.772926, lng: -84.394096, fill: 18,  demo: true },
  { id: "p377482", building: "McCamish Pavilion",                     floor: "Floor 1 (placeholder)", lat: 33.780731, lng: -84.392822, fill: 8,   demo: true },
  { id: "p279901", building: "West Village Dining Commons",           floor: "Floor 1 (placeholder)", lat: 33.779331, lng: -84.404793, fill: 76,  demo: true },
  { id: "p279193", building: "Howey School of Physics",               floor: "Floor 1 (placeholder)", lat: 33.777431, lng: -84.398552, fill: 46,  demo: true },
  { id: "p264602", building: "Marcus Nanotechnology Building",        floor: "Floor 1 (placeholder)", lat: 33.778912, lng: -84.398628, fill: 100, demo: true },
  { id: "p347966", building: "North Avenue Dining",                   floor: "Floor 1 (placeholder)", lat: 33.770973, lng: -84.391121, fill: 35,  demo: true },
  { id: "p264950", building: "Smithgall Student Services Building",   floor: "Floor 1 (placeholder)", lat: 33.774384, lng: -84.39959,  fill: 14,  demo: true },
  { id: "p264600", building: "TSRB",                                  floor: "Floor 1 (placeholder)", lat: 33.777115, lng: -84.390083, fill: 60,  demo: true },
];
