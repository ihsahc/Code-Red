// data.js — the list of dispensers. Edit this file to add, remove or move dispensers.
//
// Coordinates come from your gt-restrooms.csv (Georgia Tech campus map).
// Every building has one dispenser per floor (floor counts are approximate placeholders).
// This list is only the OFFLINE FALLBACK. Live data comes from backend/app/seed.py,
// so keep the two in sync if you change floors.
//
// Fields:
//   id        unique name for the dispenser (we reuse the CSV id)
//   building  what students see
//   floor     floor / room text shown in the popup. Several rows can share a building
//             name + lat/lng: they become ONE pin with one line per floor.
//   lat, lng  location on the map
//   fill      starting fill percentage (0-100)
//   demo      true = fake data (shows a "Demo data" badge). Set to false for your real sensor.
//   offline   true = this fake dispenser stops sending readings, so it turns gray (shows the gray pin)

const DISPENSERS = [
  { id: "p264591", building: "Clough Undergraduate Learning Commons", floor: "Floor 1", lat: 33.774868, lng: -84.3964, fill: 88, demo: true },
  { id: "p264591-f2", building: "Clough Undergraduate Learning Commons", floor: "Floor 2", lat: 33.774868, lng: -84.3964, fill: 62, demo: true },
  { id: "p264591-f3", building: "Clough Undergraduate Learning Commons", floor: "Floor 3", lat: 33.774868, lng: -84.3964, fill: 35, demo: true },
  { id: "p264591-f4", building: "Clough Undergraduate Learning Commons", floor: "Floor 4", lat: 33.774868, lng: -84.3964, fill: 12, demo: true },
  { id: "p264591-f5", building: "Clough Undergraduate Learning Commons", floor: "Floor 5", lat: 33.774868, lng: -84.3964, fill: 74, demo: true },
  { id: "p264520", building: "Gilbert Memorial Library", floor: "Floor 1", lat: 33.774426, lng: -84.39579, fill: 72, demo: true },
  { id: "p264520-f2", building: "Gilbert Memorial Library", floor: "Floor 2", lat: 33.774426, lng: -84.39579, fill: 48, demo: true },
  { id: "p264520-f3", building: "Gilbert Memorial Library", floor: "Floor 3", lat: 33.774426, lng: -84.39579, fill: 20, demo: true },
  { id: "p264520-f4", building: "Gilbert Memorial Library", floor: "Floor 4", lat: 33.774426, lng: -84.39579, fill: 9, demo: true },
  { id: "p264520-f5", building: "Gilbert Memorial Library", floor: "Floor 5", lat: 33.774426, lng: -84.39579, fill: 55, demo: true },
  { id: "klaus-atrium-pico-w", building: "Klaus Advanced Computing Building", floor: "Atrium", lat: 33.777524, lng: -84.396128, fill: 55, demo: false },
  { id: "klaus-f2", building: "Klaus Advanced Computing Building", floor: "Floor 2", lat: 33.777524, lng: -84.396128, fill: 31, demo: true },
  { id: "klaus-f3", building: "Klaus Advanced Computing Building", floor: "Floor 3", lat: 33.777524, lng: -84.396128, fill: 14, demo: true },
  { id: "klaus-f4", building: "Klaus Advanced Computing Building", floor: "Floor 4", lat: 33.777524, lng: -84.396128, fill: 0, demo: true },
  { id: "klaus-f5", building: "Klaus Advanced Computing Building", floor: "Floor 5", lat: 33.777524, lng: -84.396128, fill: 66, demo: true },
  { id: "p279898", building: "Stamps Health Services", floor: "Floor 1", lat: 33.774773, lng: -84.402885, fill: 40, demo: true },
  { id: "p279898-f2", building: "Stamps Health Services", floor: "Floor 2", lat: 33.774773, lng: -84.402885, fill: 18, demo: true },
  { id: "p473312-f1", building: "Kendeda Building", floor: "Floor 1", lat: 33.778774, lng: -84.399574, fill: 9, demo: true },
  { id: "p473312", building: "Kendeda Building", floor: "Floor 2", lat: 33.778774, lng: -84.399574, fill: 22, demo: true },
  { id: "p473312-f3", building: "Kendeda Building", floor: "Floor 3", lat: 33.778774, lng: -84.399574, fill: 0, demo: true },
  { id: "p473312-f4", building: "Kendeda Building", floor: "Floor 4", lat: 33.778774, lng: -84.399574, fill: 12, demo: true },
  { id: "p264141", building: "Skiles", floor: "Floor 1", lat: 33.773582, lng: -84.39595, fill: 12, demo: true },
  { id: "p264141-f2", building: "Skiles", floor: "Floor 2", lat: 33.773582, lng: -84.39595, fill: 6, demo: true },
  { id: "p264141-f3", building: "Skiles", floor: "Floor 3", lat: 33.773582, lng: -84.39595, fill: 0, demo: true },
  { id: "p264141-f4", building: "Skiles", floor: "Floor 4", lat: 33.773582, lng: -84.39595, fill: 3, demo: true },
  { id: "p279888", building: "Van Leer Building", floor: "Floor 1", lat: 33.775948, lng: -84.397141, fill: 5, demo: true },
  { id: "p279888-f2", building: "Van Leer Building", floor: "Floor 2", lat: 33.775948, lng: -84.397141, fill: 0, demo: true },
  { id: "p279888-f3", building: "Van Leer Building", floor: "Floor 3", lat: 33.775948, lng: -84.397141, fill: 14, demo: true },
  { id: "p279888-f4", building: "Van Leer Building", floor: "Floor 4", lat: 33.775948, lng: -84.397141, fill: 2, demo: true },
  { id: "p279888-f5", building: "Van Leer Building", floor: "Floor 5", lat: 33.775948, lng: -84.397141, fill: 9, demo: true },
  { id: "p264081", building: "College of Computing", floor: "Floor 1", lat: 33.777363, lng: -84.397354, fill: 0, demo: true },
  { id: "p264081-f2", building: "College of Computing", floor: "Floor 2", lat: 33.777363, lng: -84.397354, fill: 38, demo: true },
  { id: "p264081-f3", building: "College of Computing", floor: "Floor 3", lat: 33.777363, lng: -84.397354, fill: 0, demo: true },
  { id: "p264081-f4", building: "College of Computing", floor: "Floor 4", lat: 33.777363, lng: -84.397354, fill: 27, demo: true },
  { id: "p264568", building: "Ferst Center for the Arts", floor: "Floor 1", lat: 33.775181, lng: -84.399338, fill: 95, demo: true },
  { id: "p264568-f2", building: "Ferst Center for the Arts", floor: "Floor 2", lat: 33.775181, lng: -84.399338, fill: 81, demo: true },
  { id: "p264568-f3", building: "Ferst Center for the Arts", floor: "Floor 3", lat: 33.775181, lng: -84.399338, fill: 60, demo: true },
  { id: "p451379", building: "Instructional Center", floor: "Floor 1", lat: 33.775505, lng: -84.401314, fill: 30, demo: true },
  { id: "p451379-f2", building: "Instructional Center", floor: "Floor 2", lat: 33.775505, lng: -84.401314, fill: 52, demo: true },
  { id: "p451379-f3", building: "Instructional Center", floor: "Floor 3", lat: 33.775505, lng: -84.401314, fill: 17, demo: true },
  { id: "p451379-f4", building: "Instructional Center", floor: "Floor 4", lat: 33.775505, lng: -84.401314, fill: 44, demo: true },
  { id: "p264079", building: "Tech Tower", floor: "Floor 1", lat: 33.772457, lng: -84.39473, fill: 64, demo: true, offline: true },
  { id: "p264079-f2", building: "Tech Tower", floor: "Floor 2", lat: 33.772457, lng: -84.39473, fill: 58, demo: true },
  { id: "p264079-f3", building: "Tech Tower", floor: "Floor 3", lat: 33.772457, lng: -84.39473, fill: 21, demo: true },
  { id: "p264079-f4", building: "Tech Tower", floor: "Floor 4", lat: 33.772457, lng: -84.39473, fill: 7, demo: true },
  { id: "p261362", building: "Lyman Hall", floor: "Floor 1", lat: 33.772926, lng: -84.394096, fill: 18, demo: true },
  { id: "p261362-f2", building: "Lyman Hall", floor: "Floor 2", lat: 33.772926, lng: -84.394096, fill: 33, demo: true },
  { id: "p261362-f3", building: "Lyman Hall", floor: "Floor 3", lat: 33.772926, lng: -84.394096, fill: 4, demo: true },
  { id: "p377482", building: "McCamish Pavilion", floor: "Floor 1", lat: 33.780731, lng: -84.392822, fill: 8, demo: true },
  { id: "p377482-f2", building: "McCamish Pavilion", floor: "Floor 2", lat: 33.780731, lng: -84.392822, fill: 0, demo: true },
  { id: "p377482-f3", building: "McCamish Pavilion", floor: "Floor 3", lat: 33.780731, lng: -84.392822, fill: 11, demo: true },
  { id: "p279901", building: "West Village Dining Commons", floor: "Floor 1", lat: 33.779331, lng: -84.404793, fill: 76, demo: true },
  { id: "p279901-f2", building: "West Village Dining Commons", floor: "Floor 2", lat: 33.779331, lng: -84.404793, fill: 52, demo: true },
  { id: "p279193", building: "Howey School of Physics", floor: "Floor 1", lat: 33.777431, lng: -84.398552, fill: 46, demo: true },
  { id: "p279193-f2", building: "Howey School of Physics", floor: "Floor 2", lat: 33.777431, lng: -84.398552, fill: 70, demo: true },
  { id: "p279193-f3", building: "Howey School of Physics", floor: "Floor 3", lat: 33.777431, lng: -84.398552, fill: 25, demo: true },
  { id: "p279193-f4", building: "Howey School of Physics", floor: "Floor 4", lat: 33.777431, lng: -84.398552, fill: 9, demo: true },
  { id: "p264602", building: "Marcus Nanotechnology Building", floor: "Floor 1", lat: 33.778912, lng: -84.398628, fill: 100, demo: true },
  { id: "p264602-f2", building: "Marcus Nanotechnology Building", floor: "Floor 2", lat: 33.778912, lng: -84.398628, fill: 85, demo: true },
  { id: "p264602-f3", building: "Marcus Nanotechnology Building", floor: "Floor 3", lat: 33.778912, lng: -84.398628, fill: 40, demo: true },
  { id: "p264602-f4", building: "Marcus Nanotechnology Building", floor: "Floor 4", lat: 33.778912, lng: -84.398628, fill: 16, demo: true },
  { id: "p347966", building: "North Avenue Dining", floor: "Floor 1", lat: 33.770973, lng: -84.391121, fill: 35, demo: true },
  { id: "p347966-f2", building: "North Avenue Dining", floor: "Floor 2", lat: 33.770973, lng: -84.391121, fill: 10, demo: true },
  { id: "p264950", building: "Smithgall Student Services Building", floor: "Floor 1", lat: 33.774384, lng: -84.39959, fill: 14, demo: true },
  { id: "p264950-f2", building: "Smithgall Student Services Building", floor: "Floor 2", lat: 33.774384, lng: -84.39959, fill: 29, demo: true },
  { id: "p264950-f3", building: "Smithgall Student Services Building", floor: "Floor 3", lat: 33.774384, lng: -84.39959, fill: 41, demo: true },
  { id: "p264600", building: "TSRB", floor: "Floor 1", lat: 33.777115, lng: -84.390083, fill: 60, demo: true },
  { id: "p264600-f2", building: "TSRB", floor: "Floor 2", lat: 33.777115, lng: -84.390083, fill: 44, demo: true },
  { id: "p264600-f3", building: "TSRB", floor: "Floor 3", lat: 33.777115, lng: -84.390083, fill: 12, demo: true },
  { id: "p264600-f4", building: "TSRB", floor: "Floor 4", lat: 33.777115, lng: -84.390083, fill: 0, demo: true },
  { id: "p264600-f5", building: "TSRB", floor: "Floor 5", lat: 33.777115, lng: -84.390083, fill: 31, demo: true },
];