/** @type {import('./$types').PageServerLoad} */
export async function load({ fetch, params }) {
    /** @type {array.str} */
    let courses;
    let modules;
    let response;

    response = await fetch('/api/all/courses');
    courses = await response.json();

    response = await fetch('/api/all/modules');
    modules = await response.json();

    return {
        courses: courses,
        modules: modules,
    };
}
// Force to run in browser
export const ssr = false;
