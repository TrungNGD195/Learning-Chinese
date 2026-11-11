import { countryIllustrations } from './lessonVocabularyArt'

const star = '0,-1 .2245,-.309 .9511,-.309 .3633,.118 .5878,.809 0,.382 -.5878,.809 -.3633,.118 -.9511,-.309 -.2245,-.309'

export function CountryVocabularyIllustration({ hanzi }: { hanzi: string }) {
  const country = countryIllustrations[hanzi]
  if (!country) return null
  return <figure className="academy-word-illustration academy-country-illustration" aria-label={'Quốc kỳ ' + country.label}>
    <svg viewBox="0 0 30 20" role="img" aria-label={country.label}>
      {country.colors.length === 1 ? <><rect width="30" height="20" fill={country.colors[0]} />
        {hanzi === '越南' ? <polygon points={star} transform="translate(15 10) scale(6)" fill="#ffdf00" /> : <g fill="#ffde00">
          <polygon points={star} transform="translate(5 5) scale(3)" />
          {[[10, 2], [12, 4], [12, 7], [10, 9]].map(([x, y]) => <polygon key={`${x}-${y}`} points={star} transform={`translate(${x} ${y}) rotate(${Math.atan2(5 - y, 5 - x) * 180 / Math.PI + 90})`} />)}
        </g>}
      </> : country.colors.map((color, index) => hanzi === '法国'
        ? <rect key={index} x={index * 10} width="10" height="20" fill={color} />
        : <rect key={index} y={index * 20 / 6} width="30" height={20 / 6 + .01} fill={color} />)}
    </svg><figcaption>{country.label}</figcaption>
  </figure>
}
