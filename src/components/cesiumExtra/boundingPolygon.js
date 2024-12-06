
// Helper function to generate convex hull
export function generateHull (points) {
    // Graham Scan algorithm implementation
    function cross (o, a, b) {
        return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)
    }

    // Sort points by y, then x
    points = [...points].sort((a, b) =>
        a.y === b.y ? a.x - b.x : a.y - b.y
    )

    const lower = []
    for (let i = 0; i < points.length; i++) {
        while (lower.length >= 2 && cross(lower[lower.length - 2],
            lower[lower.length - 1],
            points[i]) <= 0) {
            lower.pop()
        }
        lower.push(points[i])
    }

    const upper = []
    for (let i = points.length - 1; i >= 0; i--) {
        while (upper.length >= 2 && cross(upper[upper.length - 2],
            upper[upper.length - 1],
            points[i]) <= 0) {
            upper.pop()
        }
        upper.push(points[i])
    }

    // Combine the lower and upper hulls
    return [...lower.slice(0, -1), ...upper.slice(0, -1)]
}

// Helper function to expand the hull
export function expandPolygon (polygon, margin) {
    // Calculate centroid
    const centroid = polygon.reduce((acc, point) => ({
        x: acc.x + point.x / polygon.length,
        y: acc.y + point.y / polygon.length
    }), { x: 0, y: 0 })

    // Expand each point outward from centroid
    return polygon.map(point => {
        const dx = point.x - centroid.x
        const dy = point.y - centroid.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        const scale = (dist + margin) / dist
        return {
            x: centroid.x + dx * scale,
            y: centroid.y + dy * scale
        }
    })
}

// Helper function to check if a point is inside a polygon
export function isPointInPolygon (x, y, polygon) {
    let inside = false
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const xi = polygon[i].x
        const yi = polygon[i].y
        const xj = polygon[j].x
        const yj = polygon[j].y

        const intersect = ((yi > y) !== (yj > y)) &&
            (x < (xj - xi) * (y - yi) / (yj - yi) + xi)
        if (intersect) inside = !inside
    }
    return inside
}

export function interpolateToGrid (points, gridSize) {
    const grid = Array(gridSize).fill().map(() => Array(gridSize).fill(0))
    const weights = Array(gridSize).fill().map(() => Array(gridSize).fill(0))

    const xStep = 1000 / gridSize
    const yStep = 1000 / gridSize

    for (let i = 0; i < gridSize; i++) {
        for (let j = 0; j < gridSize; j++) {
            const x = i * xStep
            const y = j * yStep

            points.forEach(point => {
                const distance = Math.sqrt(
                    Math.pow(x - point.x, 2) + Math.pow(y - point.y, 2)
                )
                const weight = 1 / (Math.pow(distance, 2) + 0.1)
                grid[i][j] += point.depth * weight
                weights[i][j] += weight
            })

            if (weights[i][j] > 0) {
                grid[i][j] /= weights[i][j]
            }
        }
    }

    return grid
}

export function smoothGrid (grid, sigma) {
    const size = grid.length
    const result = Array(size).fill().map(() => Array(size).fill(0))
    const kernelSize = Math.ceil(sigma * 3) * 2 + 1

    for (let i = 0; i < size; i++) {
        for (let j = 0; j < size; j++) {
            let sum = 0
            let weightSum = 0

            for (let ki = -kernelSize; ki <= kernelSize; ki++) {
                for (let kj = -kernelSize; kj <= kernelSize; kj++) {
                    const ni = i + ki
                    const nj = j + kj

                    if (ni >= 0 && ni < size && nj >= 0 && nj < size) {
                        const weight = Math.exp(-(ki * ki + kj * kj) / (2 * sigma * sigma))
                        sum += grid[ni][nj] * weight
                        weightSum += weight
                    }
                }
            }

            result[i][j] = sum / weightSum
        }
    }

    return result
}
