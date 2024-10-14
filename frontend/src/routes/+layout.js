/** @type {import('./$types').PageServerLoad} */
export async function load({ fetch, params }) {
    /** @type {array.str} */
    let response, courses, modules, locations, clubs, societies;

    response = await fetch('/api/all/course');
    courses = await response.json();

    response = await fetch('/api/all/module');
    modules = await response.json();

    response = await fetch('/api/all/location');
    locations = await response.json();

    response = await fetch('/api/all/club')
    clubs = await response.json();

    response = await fetch('/api/all/society')
    societies = await response.json();

    return {
        courses: courses,
        modules: modules,
        locations: locations,
        clubs: clubs,
        societies: societies,
    };
}
// Force to run in browser
export const ssr = false;
